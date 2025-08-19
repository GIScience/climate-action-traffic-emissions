import uuid

import pytest
import shapely
from climatoology.base.baseoperator import AoiProperties
from climatoology.base.computation import ComputationScope

from traffic_emissions.core.input import ComputeInput
from traffic_emissions.core.operator_worker import Operator


@pytest.fixture
def default_compute_input() -> ComputeInput:
    return ComputeInput()


@pytest.fixture
def default_aoi() -> shapely.MultiPolygon:
    return shapely.MultiPolygon(
        polygons=[
            [
                [
                    [12.3, 48.22],
                    [12.3, 48.34],
                    [12.48, 48.34],
                    [12.48, 48.22],
                    [12.3, 48.22],
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
    return Operator()
