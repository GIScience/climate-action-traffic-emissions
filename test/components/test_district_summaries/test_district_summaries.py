import geopandas as gpd
import geopandas.testing
import pandas as pd
import pytest
import shapely
from climatoology.base.exception import ClimatoologyUserError
from shapely.geometry.linestring import LineString

from test.conftest import TEST_RESOURCES_DIR
from traffic_emissions.components.district_summaries import (
    clean_admin_boundaries,
    get_admin_boundaries,
    get_district_summaries,
)

APPROVAL_FILES_DIR = TEST_RESOURCES_DIR / 'approved_files'

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
        't_CO2_yr': [50, 100, 100, 150],
        't_CO_yr': [5, 10, 10, 15],
        't_NOx_yr': [1, 2, 2, 3],
    },
    geometry=DISTRICT_LINE_GEOM,
    crs='EPSG:32632',
)


@pytest.mark.parametrize('ohsome_fixture', (['ohsome_client_v1', 'ohsome_client_v2']))
@pytest.mark.vcr
def test_get_district_summaries(ohsome_fixture, default_aoi, request):
    ohsome_client = request.getfixturevalue(ohsome_fixture)

    expected_df = pd.read_csv(APPROVAL_FILES_DIR / 'test_get_district_summaries.csv')

    mean_df = get_district_summaries(DISTRICT_SUMMARY_TEST_GDF, default_aoi, ohsome_client)

    pd.testing.assert_frame_equal(mean_df, expected_df)


@pytest.mark.parametrize('ohsome_fixture', (['ohsome_client_v1', 'ohsome_client_v2']))
@pytest.mark.vcr
def test_get_district_summaries_no_intersection(ohsome_fixture, test_aoi, request):
    ohsome_client = request.getfixturevalue(ohsome_fixture)

    with pytest.raises(
        ClimatoologyUserError,
        match=r'Could not be created because no administrative districts were found within the selected area',
    ):
        get_district_summaries(DISTRICT_SUMMARY_TEST_GDF, test_aoi, ohsome_client)


@pytest.mark.parametrize('ohsome_fixture', (['ohsome_client_v1', 'ohsome_client_v2']))
@pytest.mark.vcr
def test_get_admin_boundaries(ohsome_fixture, freiburg_aoi, request):
    ohsome_client = request.getfixturevalue(ohsome_fixture)

    expected_df = pd.read_csv(APPROVAL_FILES_DIR / f'test_get_admin_boundaries[{ohsome_fixture}].csv')
    expected_df['geom'] = expected_df['geom'].apply(shapely.wkt.loads)
    expected_boundaries = gpd.GeoDataFrame(expected_df, geometry='geom', crs=4326)

    boundaries = get_admin_boundaries(freiburg_aoi, ohsome_client)

    geopandas.testing.assert_geodataframe_equal(boundaries, expected_boundaries, check_like=True)


def test_clean_admin_boundaries(freiburg_aoi):
    boundaries = gpd.GeoDataFrame(geometry=[freiburg_aoi], crs='EPSG:4326')
    with pytest.raises(
        ClimatoologyUserError,
        match=r'Could not be created because no administrative districts were found within the selected area.',
    ):
        clean_admin_boundaries(boundaries, freiburg_aoi)
