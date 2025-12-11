import uuid
from unittest.mock import patch

import pytest
import shapely
from climatoology.base.baseoperator import AoiProperties
from climatoology.base.computation import ComputationScope

from traffic_emissions.core.input import ComputeInput
from traffic_emissions.core.operator_worker import Operator
from traffic_emissions.core.settings import Settings


@pytest.fixture
def default_compute_input() -> ComputeInput:
    return ComputeInput()


@pytest.fixture
def default_aoi() -> shapely.MultiPolygon:
    return shapely.MultiPolygon(
        polygons=[
            [
                [
                    [8.65, 49.39],
                    [8.65, 49.43],
                    [8.74, 49.43],
                    [8.74, 49.39],
                    [8.65, 49.39],
                ]
            ]
        ]
    )


@pytest.fixture
def small_aoi() -> shapely.Polygon:
    return shapely.box(8.673856, 49.418342, 8.677697, 49.420311)


@pytest.fixture
def road_test_aoi() -> shapely.MultiPolygon:
    return shapely.MultiPolygon(
        polygons=[
            [
                [
                    [72.883, 42.160],
                    [72.883, 42.161],
                    [72.884, 42.161],
                    [72.884, 42.160],
                    [72.883, 42.160],
                ]
            ]
        ]
    )


@pytest.fixture
def default_aoi_properties() -> AoiProperties:
    return AoiProperties(name='Heidelberg', id='heidelberg')


# The following fixtures can be ignored on plugin setup
@pytest.fixture
def compute_resources():
    with ComputationScope(uuid.uuid4()) as resources:
        yield resources


@pytest.fixture
def operator():
    default_gee_settings = Settings(
        google_earth_engine_service_account='test-account', google_earth_engine_key='test-key.json'
    )
    with (
        patch('traffic_emissions.core.operator_worker.ee.ServiceAccountCredentials'),
        patch('traffic_emissions.core.operator_worker.ee.Initialize'),
    ):
        yield Operator(default_gee_settings)


@pytest.fixture
def mock_temp_dir():
    with patch(
        'tempfile.TemporaryDirectory.__enter__',
        return_value='test/resources',
    ):
        yield


@pytest.fixture
def mock_get_pop_raster(mock_temp_dir):
    with (
        patch('traffic_emissions.components.traffic_volume.get_pop_raster'),
    ):
        yield


@pytest.fixture
def mock_get_built_up_raster(mock_temp_dir):
    with patch('traffic_emissions.components.traffic_emissions.get_built_up_raster'):
        yield
