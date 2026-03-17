import logging
import os
import tempfile
from pathlib import Path

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
import shapely
from climatoology.base.artifact import Artifact, ArtifactMetadata, Legend
from climatoology.base.artifact_creators import create_vector_artifact
from climatoology.base.computation import ComputationResources
from ohsome import OhsomeClient

from traffic_emissions.components.utils import (
    Topic,
    calculate_pop_in_buffer,
    get_colors_legend,
    get_pop_raster,
    reproject_raster,
)

log = logging.getLogger(__name__)


def traffic_volume(aoi: shapely.MultiPolygon, ohsome: OhsomeClient) -> gpd.GeoDataFrame:
    """
    Estimates mean_dtv (daily traffic volume) for each road segment.
    :return: GeoDataFrame with following columns: geometry, highway, lanes, maxspeed, mean_dtv
    """
    log.info('Calculating average daily traffic volume')
    road_gdf, total_length = get_roads(aoi, ohsome)
    road_gdf = get_road_populations(aoi, road_gdf)
    road_gdf = predict_traffic_volume(road_gdf)
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


def get_road_populations(aoi_poly: shapely.MultiPolygon, roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calculates scaling factor of population density in built-up areas and road length per capita.

    :param roads: gpd.GeoDataFrame of OSM road network
    :param aoi_poly: Polygon of AOI (EPSG: 4326)
    """
    log.debug('Calculating scaling factor')

    with tempfile.TemporaryDirectory() as tmp:
        pop_path = os.path.join(tmp, 'pop_raster.tif')
        get_pop_raster(aoi=aoi_poly, pop_path=pop_path)
        reproject_raster(raster_path=pop_path, target_crs=roads.crs)
        roads = calculate_pop_in_buffer(roads=roads, raster_path=pop_path)

    return roads


def predict_traffic_volume(gdf_road: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf_road_reg = gdf_road.copy()
    gdf_road_reg = pd.get_dummies(gdf_road_reg, columns=['highway'])

    cols_to_exclude = ['highway_living_street', 'highway_residential', 'highway_unclassified']
    existing_exclude_cols = [c for c in cols_to_exclude if c in gdf_road_reg.columns]

    if existing_exclude_cols:
        gdf_road_reg = gdf_road_reg[~gdf_road_reg[existing_exclude_cols].any(axis=1)]

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

    x_aoi = gdf_road_reg_all.drop(columns='geometry')
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
