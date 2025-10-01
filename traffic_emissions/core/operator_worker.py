# You may ask yourself why this file has such a strange name.
# Well ... python imports: https://discuss.python.org/t/warning-when-importing-a-local-module-with-the-same-name-as-a-2nd-or-3rd-party-module/27799
import locale
import logging
from typing import List

import shapely
from climatoology.base.baseoperator import AoiProperties, BaseOperator, ComputationResources, _Artifact
from climatoology.base.info import _Info
from ohsome import OhsomeClient

from traffic_emissions.components.traffic_emissions import (
    get_district_summaries,
    get_emission_artifacts,
    get_emission_chart_artifacts,
    get_emission_sums,
    traffic_emissions,
)
from traffic_emissions.components.traffic_volume import build_traffic_volume_artifact, traffic_volume
from traffic_emissions.core.info import get_info
from traffic_emissions.core.input import ComputeInput

log = logging.getLogger(__name__)


class Operator(BaseOperator[ComputeInput]):
    def __init__(self):
        super().__init__()
        self.ohsome = OhsomeClient()

    def info(self) -> _Info:
        return get_info()

    def compute(  # dead: disable
        self,
        resources: ComputationResources,
        aoi: shapely.MultiPolygon,
        aoi_properties: AoiProperties,
        params: ComputeInput,
    ) -> List[_Artifact]:
        locale.setlocale(locale.LC_ALL, '')
        road_gdf = traffic_volume(aoi, self.ohsome)
        emissions_gdf = traffic_emissions(road_gdf)
        emission_sums = get_emission_sums(emissions_gdf)
        mean_df = get_district_summaries(emissions_gdf, aoi, self.ohsome)

        artifacts = []
        traffic_volume_artifact = build_traffic_volume_artifact(road_gdf, resources)
        artifacts.append(traffic_volume_artifact)
        emission_artifacts = get_emission_artifacts(emissions_gdf, resources)
        artifacts.extend(emission_artifacts)
        if mean_df is not None:
            emission_chart_artifacts = get_emission_chart_artifacts(mean_df, aoi_properties, emission_sums, resources)
            artifacts.extend(emission_chart_artifacts)

        return artifacts
