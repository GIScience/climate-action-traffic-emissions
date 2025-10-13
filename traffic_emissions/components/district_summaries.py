import geopandas as gpd
import pandas as pd
import shapely
from ohsome import OhsomeClient

from traffic_emissions.components.traffic_emissions import log


def get_district_summaries(
    emissions_gdf_with_yearly_emissions: gpd.GeoDataFrame,
    aoi: shapely.MultiPolygon,
    ohsome_client: OhsomeClient,
) -> pd.DataFrame | None:
    log.info('Creating summary charts of emissions by city district')
    minimum_keys = ['admin_level', 'name']
    boundaries = ohsome_client.elements.geometry.post(
        properties='tags',
        bpolys=aoi,
        filter='geometry:polygon and boundary=administrative and admin_level=9',
        clipGeometry=True,
    ).as_dataframe(explode_tags=minimum_keys)
    boundaries = boundaries.loc[boundaries.geometry.geom_type.isin(('MultiPolygon', 'Polygon'))]
    boundaries = boundaries[boundaries.is_valid]
    boundaries = boundaries.reset_index(drop=True)
    if boundaries.shape[0] <= 1:
        return None
    else:
        log.debug(f'Summarising emissions into {boundaries.shape[0]} boundaries')
        # Implementation for population density is commented out for now, as it requires a 100m population raster
        # boundaries["population"] = boundaries.apply(
        #     lambda row: calculate_mean_pop_density_polygon(row.geometry),
        #     axis=1
        # )
        boundaries = boundaries.to_crs(boundaries.estimate_utm_crs())
        mean_df = get_mean_emissions(boundaries, emissions_gdf_with_yearly_emissions)

        return mean_df


def get_mean_emissions(boundaries, emissions_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
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
