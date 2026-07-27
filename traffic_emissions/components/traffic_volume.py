from pathlib import Path

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
import shapely
from climatoology.base.artifact import Artifact, ArtifactMetadata, Legend, get_climatoology_logger
from climatoology.base.artifact_creators import create_vector_artifact
from climatoology.base.computation import ComputationResources
from climatoology.base.exception import ClimatoologyUserError
from ohsome_py2.client import OhsomeClient

from traffic_emissions.components.utils import (
    Topic,
    calculate_pop_in_buffer,
    get_colors_legend,
    get_pop_raster,
)

log = get_climatoology_logger(__name__)


def traffic_volume(aoi: shapely.MultiPolygon, pop_raster_url: str, ohsome: OhsomeClient) -> gpd.GeoDataFrame:
    """
    Estimates mean_dtv (daily traffic volume) for each road segment.
    :return: GeoDataFrame with following columns: geometry, highway, lanes, maxspeed, mean_dtv
    """
    log.info('Calculating average daily traffic volume')
    road_gdf, _ = get_roads(aoi, ohsome)
    road_gdf = get_road_populations(roads=road_gdf, pop_raster_url=pop_raster_url)
    road_gdf = predict_traffic_volume(road_gdf)
    return road_gdf


def get_roads(
    aoi_poly: shapely.MultiPolygon, client: OhsomeClient, target_timestamp=None
) -> tuple[gpd.GeoDataFrame, float]:
    """
    Downloads and prepares OSM road network in the given AOI.

    :param client: ohsome client
    :param aoi_poly: Polygon of AOI (EPSG: 4326)
    :return: gdf_road: GeoDataFrame of OSM road network with highway, lanes, and maxspeed attributes
    :return: length_total: Length of the road network in the AOI in meters
    """
    log.info('Getting roads from ohsome')
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
    ]
    tag_list = [f'highway={highway_tag}' for highway_tag in highway_tags]
    ohsome_filter = f'({" or ".join(tag_list)}) and geometry:line'

    gdf_road = client.features_extraction(aoi=aoi_poly, osm_filter=ohsome_filter, clip=True)
    gdf_road = gdf_road[['osm_id', 'osm_type', 'geom', 'highway', 'lanes', 'maxspeed']]

    log.info('Finished getting roads from ohsome')
    if len(gdf_road) == 0:
        raise ClimatoologyUserError(
            'There are no roads in the selected area for which traffic emissions can be estimated. Please select a larger area. Traffic emissions cannot be estimated for residential or other minor roads.'
        )

    lanes = pd.to_numeric(gdf_road['lanes'], errors='coerce')
    gdf_road['lanes'] = lanes.where((lanes % 1 == 0) & (lanes.between(0, 255))).astype('Int8')
    gdf_road = gdf_road.to_crs(gdf_road.estimate_utm_crs())
    length_total = client.features_stats(aoi=aoi_poly, osm_filter=ohsome_filter, measure='length')
    return gdf_road, length_total


def get_road_populations(roads: gpd.GeoDataFrame, pop_raster_url: str) -> gpd.GeoDataFrame:
    """
    Calculates scaling factor of population density in built-up areas and road length per capita.

    :param pop_raster_url: URL of the population raster in the S3 storage
    :param roads: gpd.GeoDataFrame of OSM road network
    """
    log.debug('Calculating scaling factor')
    buf_10k = roads.geometry.buffer(10000)
    projected_buffer = buf_10k.to_crs(4326)

    # we could feed the raster URL directly to raster_status but due to
    # https://github.com/perrygeo/python-rasterstats/issues/313 this is ineffective
    # We therefore read the raster manually first
    pop_raster, pop_transform = get_pop_raster(target_geoms=projected_buffer, pop_raster_url=pop_raster_url)
    roads['pop_mean_10km'] = calculate_pop_in_buffer(
        roads=projected_buffer, pop_raster=pop_raster, pop_transform=pop_transform
    )

    return roads


def predict_traffic_volume(gdf_road: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf_road_reg = gdf_road.copy()
    gdf_road_reg = pd.get_dummies(gdf_road_reg, columns=['highway'])

    replacement_dict = {
        'walk': 5,
        'DE:urban': 50,
        'none': np.nan,
        'variable': np.nan,
    }
    gdf_road_reg = gdf_road_reg.replace(replacement_dict)
    gdf_road_reg['lanes'] = gdf_road_reg['lanes'].astype('Int64')
    gdf_road_reg['maxspeed'] = pd.to_numeric(gdf_road_reg['maxspeed'], errors='coerce').astype('Int64')
    gdf_road_reg_all = gdf_road_reg.copy()

    model = joblib.load(Path('resources/model.joblib'))
    imputer = joblib.load(Path('resources/imputer.joblib'))

    x_aoi = gdf_road_reg_all.drop(columns='geom')
    train_cols = imputer.feature_names_in_
    x_aoi = x_aoi.reindex(columns=train_cols, fill_value=0)
    x_aoi_imp = imputer.transform(x_aoi)

    pred_all = model.predict(x_aoi_imp)
    gdf_road_reg_all['mean_dtv'] = pred_all
    gdf_road = gdf_road.merge(gdf_road_reg_all[['mean_dtv']], left_index=True, right_index=True)
    gdf_road = gdf_road[gdf_road.geometry.geom_type.isin(['LineString', 'MultiLineString'])]

    return gdf_road


def build_traffic_volume_artifact(road_gdf: gpd.GeoDataFrame, resources: ComputationResources) -> Artifact:
    color, legend = get_colors_legend(road_gdf['mean_dtv'])
    road_gdf['color'] = color
    road_gdf['mean_dtv'] = road_gdf['mean_dtv'].round()
    traffic_volume_metadata = ArtifactMetadata(
        name='Estimated average daily traffic volume',
        tags={Topic.MAPS},
        filename='traffic_volume',
        summary='Estimated average number of vehicles traveling on each road segment per day',
        description=Path('resources/artifact_descriptions/traffic_volume_description.md').read_text(),
    )

    return create_vector_artifact(
        data=road_gdf,
        metadata=traffic_volume_metadata,
        legend=Legend(legend_data=legend),
        label='mean_dtv',
        resources=resources,
    )
