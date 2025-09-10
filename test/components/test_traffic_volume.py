from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from approvaltests import verify
from shapely.geometry import LineString
from vcr import use_cassette

from traffic_emissions.components.traffic_volume import (
    assign_traffic,
    calculate_mean_pop_density_polygon,
    get_roads,
    get_scaling_factor,
    traffic_volume,
)

LINE_GEOM = gpd.GeoSeries(
    [LineString([(325193.9834442865, 4669724.10105637), (325111.5841199331, 4669734.855883078)]) for _ in range(6)]
)


@use_cassette
def test_get_roads(operator, road_test_aoi):
    road_gdf, total_length = get_roads(road_test_aoi, operator.ohsome)
    verify(road_gdf.to_csv())
    assert total_length == 83.0982247188029


def test_get_scaling_factor(default_aoi):
    total_length = 100000
    expected = 1.56
    scaling_factor = get_scaling_factor(default_aoi, total_length)
    assert round(scaling_factor, 2) == expected


def test_calculate_mean_pop_density_polygon(default_aoi):
    pop_path = 'resources/pop_dens.tif'
    mean_pop_dens_aoi, pop_sum_aoi = calculate_mean_pop_density_polygon(pop_path, default_aoi)
    assert round(mean_pop_dens_aoi, 2) == 1358.02
    assert round(pop_sum_aoi, 0) == 74691


def test_assign_traffic():
    road_gdf = gpd.GeoDataFrame(
        {
            'highway': ['trunk_link', 'motorway_link', 'residential', 'motorway', 'unclassified', 'tertiary_link'],
            'lanes': pd.Series([2, np.nan, np.nan, 5, 4, 6], dtype='Int8'),
        },
        geometry=LINE_GEOM,
    )
    scaling = 1.0
    expected = gpd.GeoDataFrame(
        {
            'highway': ['trunk', 'motorway_link', 'residential', 'motorway_4', 'unclassified_3', 'tertiary_5'],
            'lanes': pd.Series([2, np.nan, np.nan, 5, 4, 6], dtype='Int8'),
            'mean_dtv': [16202.2, 9320.0, 5457.2, 63882.94, 9400.0, 15340.0],
        },
        geometry=LINE_GEOM,
    )
    received = assign_traffic(road_gdf, scaling)
    pd.testing.assert_frame_equal(
        received.round(1).drop(columns='geometry'), expected.round(1).drop(columns='geometry'), check_dtype=False
    )


def test_assign_traffic_with_scaling():
    road_gdf = gpd.GeoDataFrame(
        {
            'highway': ['trunk', 'motorway_link', 'residential', 'motorway', 'unclassified', 'tertiary_link'],
            'lanes': pd.Series([2, np.nan, np.nan, 5, 4, 6], dtype='Int8'),
        },
        geometry=LINE_GEOM,
    )
    scaling = 0.5
    expected = gpd.GeoDataFrame(
        {
            'highway': ['trunk', 'motorway_link', 'residential', 'motorway_4', 'unclassified_3', 'tertiary_5'],
            'lanes': pd.Series([2, np.nan, np.nan, 5, 4, 6], dtype='Int8'),
            'mean_dtv': [8101.1, 9320.0, 2728.6, 63882.94, 4700.0, 7670.0],
        },
        geometry=LINE_GEOM,
    )
    received = assign_traffic(road_gdf, scaling)
    pd.testing.assert_frame_equal(
        received.round(1).drop(columns='geometry'), expected.round(1).drop(columns='geometry'), check_dtype=False
    )


@pytest.fixture
def population_density():
    with patch('traffic_emissions.components.traffic_volume.calculate_mean_pop_density_polygon') as mock:
        mock.return_value = (1300.0, 70000.0)
        yield mock


@use_cassette
def test_traffic_volume(operator, small_aoi, population_density):
    road_gdf = traffic_volume(small_aoi, operator.ohsome)
    verify(road_gdf.to_csv())
