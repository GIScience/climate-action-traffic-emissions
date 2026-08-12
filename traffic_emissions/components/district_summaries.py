import warnings

import geopandas as gpd
import pandas as pd
import shapely
from climatoology.base.exception import ClimatoologyUserError
from climatoology.base.logging import get_climatoology_logger
from ohsome_py2.client import OhsomeClient

log = get_climatoology_logger(__name__)


def get_district_summaries(
    emissions_gdf_with_yearly_emissions: gpd.GeoDataFrame,
    aoi: shapely.MultiPolygon,
    ohsome_client: OhsomeClient,
) -> pd.DataFrame | None:
    log.info('Creating summary charts of emissions by city district')
    boundaries = get_admin_boundaries(aoi, ohsome_client=ohsome_client)

    log.debug(f'Summarising emissions into {boundaries.shape[0]} boundaries')
    mean_df = get_mean_emissions(boundaries, emissions_gdf_with_yearly_emissions)

    return mean_df


def get_admin_boundaries(
    aoi: shapely.MultiPolygon, ohsome_client: OhsomeClient, start_level: int = 9, stop_level: int = 10
) -> gpd.GeoDataFrame:
    admin_levels = list(range(start_level, stop_level + 1))
    osm_filter = f'geometry:polygon and boundary=administrative and admin_level in {tuple(admin_levels)}'

    log.info('Querying admin boundaries from ohsome')
    all_boundaries = ohsome_client.features_extraction(
        aoi=aoi,
        osm_filter=osm_filter,
        tags='exploded',
        clip=False,
    )

    log.info('Finished querying admin boundaries from ohsome')
    all_boundaries = clean_admin_boundaries(boundaries=all_boundaries, aoi=aoi)

    boundaries = None
    for level, group in all_boundaries.groupby('admin_level', sort=True):
        if boundaries is None:
            boundaries = group.copy()
        else:
            already_covered = shapely.union_all(boundaries.geometry)
            filler_boundaries = group[~group.geometry.within(already_covered.buffer(1e-6))]
            log.debug(f'Added {len(filler_boundaries)} from admin level {level}')
            boundaries = pd.concat([boundaries, filler_boundaries])

        already_covered = shapely.union_all(boundaries.geometry)
        if already_covered.buffer(1e-6).contains(aoi):
            break

    return boundaries


def clean_admin_boundaries(boundaries: gpd.GeoDataFrame, aoi: shapely.MultiPolygon) -> gpd.GeoDataFrame:
    clipped_geometries = boundaries.intersection(aoi)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Geometry is in a geographic CRS', category=UserWarning)
        boundaries['prop_covered'] = clipped_geometries.area / boundaries.area

    boundaries = boundaries.loc[boundaries.geometry.geom_type.isin(('MultiPolygon', 'Polygon'))]
    boundaries = boundaries[boundaries['prop_covered'] > 0.9]
    boundaries = boundaries[boundaries.is_valid]

    if boundaries.shape[0] < 2:
        raise ClimatoologyUserError(
            'Could not be created because no administrative districts were found within the selected area.'
        )

    boundaries['admin_level'] = boundaries['admin_level'].astype(int)
    boundaries = boundaries[['geom', 'admin_level', 'name']]

    boundaries = boundaries.reset_index(drop=True)
    return boundaries


def get_mean_emissions(boundaries, emissions_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    boundaries = boundaries.to_crs(boundaries.estimate_utm_crs())
    boundaries['area_km2'] = boundaries.geometry.area / 1e6
    emissions_gdf = emissions_gdf[emissions_gdf.geometry.type.isin(['LineString', 'MultiLineString'])]
    emissions_gdf = emissions_gdf.overlay(boundaries, how='identity', keep_geom_type=False)

    mean_df = emissions_gdf.groupby('name')[['t_CO2_km_yr', 't_CO_km_yr', 't_NOx_km_yr']].mean().reset_index()
    emissions_per_area_df = emissions_gdf.groupby('name', as_index=False).agg(
        {'t_CO2_yr': 'sum', 't_CO_yr': 'sum', 't_NOx_yr': 'sum', 'area_km2': 'first'}
    )

    emissions_per_area_df['t_CO2_km2_yr'] = emissions_per_area_df['t_CO2_yr'] / (emissions_per_area_df['area_km2'])
    emissions_per_area_df['t_CO_km2_yr'] = emissions_per_area_df['t_CO_yr'] / (emissions_per_area_df['area_km2'])
    emissions_per_area_df['t_NOx_km2_yr'] = emissions_per_area_df['t_NOx_yr'] / (emissions_per_area_df['area_km2'])

    mean_df = mean_df.merge(emissions_per_area_df[['name', 't_CO2_km2_yr', 't_CO_km2_yr', 't_NOx_km2_yr']], on='name')

    return mean_df
