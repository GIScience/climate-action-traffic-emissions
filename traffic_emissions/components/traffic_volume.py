import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio
import shapely
from climatoology.base.artifact import _Artifact, create_geojson_artifact
from climatoology.base.computation import ComputationResources
from ohsome import OhsomeClient
from rasterio.mask import mask

from traffic_emissions.components.utils import POP_DENS_BERLIN, ROAD_LENGTH_PER_CAPITA_BERLIN, Topic, get_colors_legend

log = logging.getLogger(__name__)


def traffic_volume(aoi: shapely.MultiPolygon, ohsome: OhsomeClient) -> gpd.GeoDataFrame:
    log.info('Calculating average daily traffic volume')
    road_gdf, total_length = get_roads(aoi, ohsome)
    scaling = get_scaling_factor(aoi, total_length)
    road_gdf = assign_traffic(road_gdf, scaling)
    return road_gdf


def get_roads(aoi_poly: shapely.MultiPolygon, client: OhsomeClient) -> tuple[gpd.GeoDataFrame, float]:
    """
    Downloads and prepares OSM road network in the given AOI.

    :param client: Ohsome client
    :param aoi_poly: Polygon of AOI (EPSG: 4326)
    :return: gdf_road: GeoDataFrame of OSM road network with highway, lanes, and maxspeed attributes
    :return: length_total: Length of the road network in the AOI in meters
    """
    log.debug('Getting roads from OSM')

    highway_tags = [
        'motorway',
        'motorway_link',
        'motorway_junction',
        'trunk',
        'trunk_link',
        'primary',
        'primary_link',
        'secondary',
        'secondary_link',
        'tertiary',
        'tertiary_link',
        'residential',
        'living_street',
        'unclassified',
    ]
    tag_list = [f'highway={highway_tag}' for highway_tag in highway_tags]
    ohsome_filter = f'({" or ".join(tag_list)}) and geometry:line'

    gdf_road = client.elements.geometry.post(
        bpolys=aoi_poly, time=client.end_timestamp, filter=ohsome_filter, clipGeometry=True, properties='tags'
    ).as_dataframe()
    tags_df = gdf_road['@other_tags'].apply(pd.Series)
    gdf_road = pd.concat([gdf_road, tags_df], axis=1)
    gdf_road = gdf_road[['geometry', 'highway', 'lanes', 'maxspeed']]
    lanes = pd.to_numeric(gdf_road['lanes'], errors='coerce')
    gdf_road['lanes'] = lanes.where((lanes % 1 == 0) & (lanes.between(0, 255))).astype('Int8')
    gdf_road = gdf_road.to_crs(gdf_road.estimate_utm_crs())
    length_total = gdf_road.length.sum()
    return gdf_road, length_total


def get_scaling_factor(aoi_poly: shapely.MultiPolygon, length_total: float) -> float:
    """
    Calculates scaling factor of population density in built-up areas and road length per capita.

    :param aoi_poly: Polygon of AOI (EPSG: 4326)
    :param length_total: Length of the road network in the AOI in meters
    :return: scaling_factor: Scaling factor of population density and road length per capita
    """
    log.debug('Calculating scaling factor')
    pop_path = 'resources/pop_dens.tif'
    mean_pop_dens_aoi, pop_sum_aoi = calculate_mean_pop_density_polygon(pop_path, aoi_poly)
    length_per_capita_aoi = length_total / pop_sum_aoi
    pop_scaling_factor = mean_pop_dens_aoi / POP_DENS_BERLIN
    length_scaling_factor = ROAD_LENGTH_PER_CAPITA_BERLIN / length_per_capita_aoi
    scaling_factor = pop_scaling_factor * length_scaling_factor
    return scaling_factor


def calculate_mean_pop_density_polygon(raster_path: str, polygon: shapely.MultiPolygon) -> tuple[float, float]:
    """
    Calculates mean and total population in the given polygons using the GHS_POP population raster.

    :param raster_path: filepath of GHS_POP population raster (EPSG: 4326)
    :param polygon: Polygon of AOI for which population density is calculated (EPSG: 4326)
    :return: mean_value: mean population per grid cell in the given polygons
    :return: sum_value: total population in the given polygons
    """
    with rasterio.open(raster_path) as src:
        out_image, _ = mask(src, [polygon], crop=True, nodata=-999)
        valid_data = out_image[out_image != -999]
        if valid_data.size == 0:
            raise ValueError(f'No valid population data found in {raster_path} for the given area of interest.')

        mean_value = valid_data.mean()
        sum_value = valid_data.sum()
        return mean_value, sum_value


def assign_traffic(gdf_road: gpd.GeoDataFrame, scaling: float) -> gpd.GeoDataFrame:
    """
    Assigns mean daily traffic volumes per road class for Berlin to OSM road geometries in the AOI, scaled by population
    density. Calculates deviations between assigned traffic volumes and traffic counts.

    :param gdf_road: GeoDataFrame of OSM road network with traffic counts of Heidelberg and Mannheim
    :param scaling: Scaling factor of population density
    :return: gdf_road: GeoDataFrame of OSM road network with estimated traffic volumes
    """

    def update_highway(row):
        if row['highway'] == 'trunk_link':
            row['highway'] = 'trunk'
        elif row['highway'] == 'tertiary_link':
            row['highway'] = 'tertiary'

        if not pd.isnull(row['lanes']):
            if row['highway'] in ['motorway_link', 'unclassified'] and row['lanes'] > 3:
                row['lanes'] = 3
            if row['highway'] in ['motorway', 'residential'] and row['lanes'] > 4:
                row['lanes'] = 4
            if row['highway'] in ['primary', 'secondary', 'tertiary'] and row['lanes'] > 5:
                row['lanes'] = 5

        if row['highway'] in ['living_street', 'trunk', 'primary_link', 'secondary_link']:
            return row['highway']
        if not pd.isnull(row['lanes']):
            return f'{row["highway"]}_{int(row["lanes"])}'
        else:
            return row['highway']

    gdf_road['highway'] = gdf_road.apply(update_highway, axis=1)

    mean_dtv = pd.read_csv('resources/mean_dtv_berlin.csv')
    mean_dtv_mask = ~mean_dtv['highway'].str.contains('motorway', na=False)
    mean_dtv.loc[mean_dtv_mask, 'mean_dtv'] = mean_dtv.loc[mean_dtv_mask, 'mean_dtv'] * scaling
    gdf_road = gdf_road.merge(mean_dtv, on='highway', how='left')
    return gdf_road


def build_traffic_volume_artifact(road_gdf: gpd.GeoDataFrame, resources: ComputationResources) -> _Artifact:
    color, legend = get_colors_legend(40000, road_gdf['mean_dtv'])

    return create_geojson_artifact(
        features=road_gdf.geometry,
        layer_name='Estimated average daily traffic volume',
        caption='Estimated average number of vehicles traveling on each road segment per day',
        description=Path('resources/artifact_descriptions/traffic_volume_description.md').read_text(),
        color=color,
        legend_data=legend,
        label=road_gdf['mean_dtv'].round(),
        resources=resources,
        filename='traffic_volume',
        tags={Topic.MAPS},
    )
