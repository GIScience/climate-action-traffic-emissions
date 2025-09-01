# You may ask yourself why this file has such a strange name.
# Well ... python imports: https://discuss.python.org/t/warning-when-importing-a-local-module-with-the-same-name-as-a-2nd-or-3rd-party-module/27799
import logging
from typing import List

import shapely
from climatoology.base.baseoperator import AoiProperties, BaseOperator, ComputationResources, _Artifact
from climatoology.base.info import _Info

from traffic_emissions.components.traffic_emissions import (
    get_emission_artifacts,
    traffic_emissions,
)
from traffic_emissions.components.traffic_volume import build_traffic_volume_artifact, traffic_volume
from traffic_emissions.core.info import get_info
from traffic_emissions.core.input import ComputeInput

log = logging.getLogger(__name__)


class Operator(BaseOperator[ComputeInput]):
    def info(self) -> _Info:
        return get_info()

    def compute(  # dead: disable
        self,
        resources: ComputationResources,
        aoi: shapely.MultiPolygon,
        aoi_properties: AoiProperties,
        params: ComputeInput,
    ) -> List[_Artifact]:
        road_gdf = traffic_volume(aoi)
        emissions_gdf = traffic_emissions(road_gdf)

        artifacts = []
        traffic_volume_artifact = build_traffic_volume_artifact(road_gdf, resources)
        artifacts.append(traffic_volume_artifact)
        emission_artifacts = get_emission_artifacts(emissions_gdf, resources)
        artifacts.extend(emission_artifacts)

        return artifacts
