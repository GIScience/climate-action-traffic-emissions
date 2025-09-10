from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
from approvaltests import verify
from climatoology.base.artifact import ArtifactModality
from shapely.geometry import LineString, Polygon
from vcr import use_cassette

from test.components.test_traffic_volume import LINE_GEOM
from traffic_emissions.components.traffic_emissions import (
    calculate_emissions,
    get_district_summaries,
    get_emission_chart_artifacts,
    get_emission_sums,
    plot_emission_bar,
    preprocess,
    traffic_emissions,
)

DISTRICT_LINE_GEOM = gpd.GeoSeries(
    [
        LineString([(476917, 5473595), (477285, 5473606)]),
        LineString([(476917, 5473595), (477285, 5473606)]),
        LineString([(476678, 5472913), (477284, 5472913)]),
        LineString([(476678, 5472913), (477284, 5472913)]),
    ]
)

DISTRICT_SUMMARY_TEST_GDF = gpd.GeoDataFrame(
    {
        't_CO2_km_yr': [50, 100, 100, 150],
        't_CO_km_yr': [5, 10, 10, 15],
        't_NOx_km_yr': [1, 2, 2, 3],
    },
    geometry=DISTRICT_LINE_GEOM,
)


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


def test_get_emission_sums():
    gdf = gpd.GeoDataFrame(
        {
            't_CO2_km_yr': [100, 100],
            't_CO_km_yr': [100, 100],
            't_NOx_km_yr': [100, 100],
        },
        geometry=LINE_GEOM,
    )
    expected_sums = {
        'CO2': 0.0166,
        'CO': 0.0166,
        'NOx': 0.0166,
    }
    emission_sums = get_emission_sums(gdf)
    assert {k: round(v, 4) for k, v in emission_sums.items()} == expected_sums


@use_cassette
def test_get_district_summaries(operator, default_aoi):
    mean_df = get_district_summaries(DISTRICT_SUMMARY_TEST_GDF, default_aoi, operator.ohsome)
    verify(mean_df.to_csv())


def test_get_district_summaries_no_intersection(operator, road_test_aoi):
    assert get_district_summaries(DISTRICT_SUMMARY_TEST_GDF, road_test_aoi, operator.ohsome) is None


def test_plot_emission_bar():
    df = pd.DataFrame(
        {
            'name': ['Minas Tirith'],
            't_CO2_km_yr': [100],
        }
    )
    fig = plot_emission_bar(df, 'CO2', 'Gondor')
    np.testing.assert_array_equal(fig['data'][0]['name'], 't_CO2_km_yr')
    np.testing.assert_array_equal(fig['data'][0]['y'], np.array(['Minas Tirith', 'Gondor']))


def test_get_emission_chart_artifacts(default_aoi_properties, compute_resources):
    df = pd.DataFrame(
        {
            'name': ['Minas Tirith'],
            't_CO2_km_yr': [100],
            't_CO_km_yr': [10],
            't_NOx_km_yr': [1],
        }
    )
    emission_sums = {'CO2': 1000.123, 'CO': 100.123, 'NOx': 10.123}
    expected_titles = [
        'Mean annual CO2 emissions [t/road-km]',
        'Mean annual CO emissions [t/road-km]',
        'Mean annual NOx emissions [t/road-km]',
    ]
    artifacts = get_emission_chart_artifacts(df, default_aoi_properties, emission_sums, compute_resources)
    for artifact, expected_title in zip(artifacts, expected_titles):
        assert artifact.name == expected_title
        assert artifact.modality == ArtifactModality.CHART_PLOTLY
        assert artifact.primary is False
