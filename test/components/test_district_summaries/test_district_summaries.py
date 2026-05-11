import geopandas as gpd
import pytest
from approvaltests import verify
from climatoology.base.exception import ClimatoologyUserError
from shapely.geometry.linestring import LineString

from traffic_emissions.components.district_summaries import (
    clean_admin_boundaries,
    get_admin_boundaries,
    get_district_summaries,
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
        't_CO2_yr': [50, 100, 100, 150],
        't_CO_yr': [5, 10, 10, 15],
        't_NOx_yr': [1, 2, 2, 3],
    },
    geometry=DISTRICT_LINE_GEOM,
    crs='EPSG:32632',
)


@pytest.mark.vcr
def test_get_district_summaries(operator, default_aoi):
    mean_df = get_district_summaries(DISTRICT_SUMMARY_TEST_GDF, default_aoi, operator.ohsome)
    verify(mean_df.to_csv())


@pytest.mark.vcr
def test_get_district_summaries_no_intersection(operator, test_aoi):
    with pytest.raises(
        ClimatoologyUserError,
        match=r'Could not be created because no administrative districts were found within the selected area',
    ):
        get_district_summaries(DISTRICT_SUMMARY_TEST_GDF, test_aoi, operator.ohsome)


@pytest.mark.vcr
def test_get_admin_boundaries(operator, freiburg_aoi):
    boundaries = get_admin_boundaries(operator.ohsome, freiburg_aoi)
    verify(boundaries.to_csv())


def test_clean_admin_boundaries(freiburg_aoi):
    boundaries = gpd.GeoDataFrame(geometry=[freiburg_aoi], crs='EPSG:4326')
    with pytest.raises(
        ClimatoologyUserError,
        match=r'Could not be created because no administrative districts were found within the selected area.',
    ):
        clean_admin_boundaries(boundaries, freiburg_aoi)
