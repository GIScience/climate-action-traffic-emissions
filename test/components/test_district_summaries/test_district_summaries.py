import geopandas as gpd
import pytest
from approvaltests import verify
from climatoology.base.exception import ClimatoologyUserError
from vcr import use_cassette

from traffic_emissions.components.district_summaries import clean_admin_boundaries, get_admin_boundaries


@use_cassette('test/resources/vcr_cassettes/test_get_admin_boundaries.yaml')
def test_get_admin_boundaries(operator, karlsruhe_aoi):
    boundaries = get_admin_boundaries(operator.ohsome, karlsruhe_aoi)
    verify(boundaries.to_csv())


def test_clean_admin_boundaries(karlsruhe_aoi):
    boundaries = gpd.GeoDataFrame(geometry=[karlsruhe_aoi], crs='EPSG:4326')
    with pytest.raises(
        ClimatoologyUserError,
        match=r'Could not be created because no administrative districts were found within the selected area.',
    ):
        clean_admin_boundaries(boundaries, karlsruhe_aoi)
