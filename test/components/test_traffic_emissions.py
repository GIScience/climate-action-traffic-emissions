from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
from approvaltests import verify
from shapely.geometry import LineString, Polygon

from test.components.test_traffic_volume import LINE_GEOM
from traffic_emissions.components.traffic_emissions import calculate_emissions, preprocess, traffic_emissions


def test_preprocess():
    roads = gpd.GeoDataFrame(
        {'highway': ['residential', 'motorway', 'secondary'], 'maxspeed': [30, 130, 90]},
        geometry=[LineString([(0, 0), (1, 0)]), LineString([(10, 0), (20, 0)]), LineString([(0, 6), (0, 10)])],
    )

    built_up = gpd.GeoDataFrame(
        {'id': [1]},
        geometry=[Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])],
    )

    with patch('traffic_emissions.components.traffic_emissions.gpd.read_file', return_value=built_up):
        processed = preprocess(roads)

    assert processed.loc[0, 'road_type'] == 'inside'
    assert processed.loc[1, 'road_type'] == 'motorway'
    assert processed.loc[2, 'road_type'] == 'outside'


def test_calculate_emissions():
    roads = gpd.GeoDataFrame(
        {
            'mean_dtv': [1000, 1000, 1000, 1000, 1000, 1000],
            'road_type': ['inside', None, 'motorway', 'inside', 'outside', 'squirrel'],
            'maxspeed': [50, np.nan, np.nan, np.nan, np.nan, np.nan],
        },
        geometry=LINE_GEOM,
    )
    expected_co2 = pd.Series([59.05, np.nan, 74.46, 71.9, 56.21, np.nan], name='t_CO2_km_yr')
    expected_co = pd.Series([0.97, np.nan, 1.23, 1.19, 0.93, np.nan], name='t_CO_km_yr')
    expected_nox = pd.Series([0.16, np.nan, 0.2, 0.19, 0.15, np.nan], name='t_NOx_km_yr')
    received = calculate_emissions(roads)

    pd.testing.assert_series_equal(received['t_CO2_km_yr'].round(2), expected_co2)
    pd.testing.assert_series_equal(received['t_CO_km_yr'].round(2), expected_co)
    pd.testing.assert_series_equal(received['t_NOx_km_yr'].round(2), expected_nox)


def test_traffic_emissions():
    roads = gpd.GeoDataFrame(
        {
            'highway': ['residential', 'motorway', 'secondary', 'tertiary_2', 'secondary_link', 'secondary_2'],
            'maxspeed': [30, 130, 90, np.nan, 50, 50],
            'mean_dtv': [1000, 1000, 1000, 6238.3, 9980.6, 12056.4],
        },
        geometry=LINE_GEOM,
    )
    emissions_gdf = traffic_emissions(roads)
    verify(emissions_gdf.to_csv())
