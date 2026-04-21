import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
import rasterio
import shapely
from climatoology.base.baseoperator import AoiProperties
from climatoology.base.computation import ComputationScope
from pydantic import SecretStr
from shapely import Polygon

from traffic_emissions.core.input import ComputeInput
from traffic_emissions.core.operator_worker import Operator
from traffic_emissions.core.settings import Settings

TEST_RESOURCES_DIR = Path(__file__).parent / 'resources'


@pytest.fixture
def default_compute_input() -> ComputeInput:
    return ComputeInput()


@pytest.fixture
def default_aoi() -> shapely.MultiPolygon:
    return shapely.MultiPolygon(
        polygons=[
            Polygon(
                [
                    [8.65, 49.39],
                    [8.65, 49.43],
                    [8.74, 49.43],
                    [8.74, 49.39],
                    [8.65, 49.39],
                ]
            )
        ]
    )


@pytest.fixture
def small_aoi() -> shapely.Polygon:
    return shapely.box(8.673856, 49.418342, 8.677697, 49.420311)


@pytest.fixture
def road_test_aoi() -> shapely.MultiPolygon:
    return shapely.MultiPolygon(
        polygons=[
            Polygon(
                [
                    [72.883, 42.160],
                    [72.883, 42.161],
                    [72.884, 42.161],
                    [72.884, 42.160],
                    [72.883, 42.160],
                ]
            )
        ]
    )


@pytest.fixture
def karlsruhe_aoi() -> shapely.MultiPolygon:
    return shapely.MultiPolygon(
        polygons=[
            Polygon(
                [
                    [8.4123, 48.9915],
                    [8.4185, 48.9915],
                    [8.4185, 48.9946],
                    [8.4123, 48.9946],
                    [8.4123, 48.9915],
                ]
            )
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
    default_settings = Settings(
        data_s3_access_key='test-key',
        data_s3_secret_key=SecretStr('test-secret-key'),
        data_s3_endpoint='https://test-endpoint',
        data_s3_bucket_name='test-bucket',
        pop_raster_object_name='pop',
        built_raster_object_name='built',
    )
    yield Operator(default_settings)


@pytest.fixture
def mock_get_pop_raster():
    raster_path = TEST_RESOURCES_DIR / 'pop_raster.tif'

    def _mocked_function(*args, **kwargs):
        with rasterio.open(raster_path) as src:
            array = src.read(1)
            return array, src.transform

    with patch(
        'traffic_emissions.components.traffic_volume.get_pop_raster',
        side_effect=_mocked_function,
    ) as mock_func:
        yield mock_func


@pytest.fixture
def mock_get_built_up_raster():
    raster_path = TEST_RESOURCES_DIR / 'built_up_raster.tif'

    def _mocked_function(*args, **kwargs):
        with rasterio.open(raster_path) as src:
            array = src.read(1)
            return {
                'array': array,
                'transform': src.transform,
                'crs': src.crs,
                'nodata': src.nodata,
            }

    with patch(
        'traffic_emissions.components.traffic_emissions.get_built_up_raster',
        side_effect=_mocked_function,
    ) as mock_func:
        yield mock_func


@pytest.fixture
def mock_s3_built_up_raster():
    test_raster_path = TEST_RESOURCES_DIR / 'built_up_raster.tif'
    fake_url = 'https://fake-s3-url/built_up.tif'
    dataset = rasterio.open(test_raster_path)
    with patch('rasterio.open', return_value=dataset):
        yield fake_url
    dataset.close()
