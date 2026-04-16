# You may ask yourself why this file has such a strange name.
# Well ... python imports: https://discuss.python.org/t/warning-when-importing-a-local-module-with-the-same-name-as-a-2nd-or-3rd-party-module/27799
import logging
from typing import List

import geopandas as gpd
import rasterio
import shapely
from climatoology.base.baseoperator import AoiProperties, Artifact, BaseOperator, ComputationResources
from climatoology.base.exception import ClimatoologyUserError
from climatoology.base.plugin_info import PluginInfo
from ohsome import OhsomeClient
from rasterio.session import AWSSession

from traffic_emissions.components.district_summaries import get_district_summaries
from traffic_emissions.components.traffic_emissions import (
    get_emission_artifacts,
    get_emission_chart_artifacts,
    get_emission_sums,
    traffic_emissions,
)
from traffic_emissions.components.traffic_volume import build_traffic_volume_artifact, traffic_volume
from traffic_emissions.core.info import get_info
from traffic_emissions.core.input import ComputeInput
from traffic_emissions.core.settings import Settings

log = logging.getLogger(__name__)


class Operator(BaseOperator[ComputeInput]):
    def __init__(self, settings: Settings):
        super().__init__()
        self.ohsome = OhsomeClient()
        self.s3_client = AWSSession(
            endpoint_url=settings.data_s3_endpoint,
            aws_access_key_id=settings.data_s3_access_key,
            aws_secret_access_key=settings.data_s3_secret_key.get_secret_value(),
        )
        self.pop_raster_url = f's3://{settings.data_s3_bucket_name}/{settings.pop_raster_object_name}'
        self.built_raster_url = f's3://{settings.data_s3_bucket_name}/{settings.built_raster_object_name}'

    def info(self) -> PluginInfo:
        return get_info()

    def compute(  # dead: disable
        self,
        resources: ComputationResources,
        aoi: shapely.MultiPolygon,
        aoi_properties: AoiProperties,
        params: ComputeInput,
    ) -> List[Artifact]:
        self.check_aoi(aoi, aoi_properties)

        # this is the process to access S3 stored rasters directly, the alternative is to use pre-signed URLs
        with rasterio.Env(self.s3_client, AWS_VIRTUAL_HOSTING=False):
            road_gdf = traffic_volume(aoi=aoi, ohsome=self.ohsome, pop_raster_url=self.pop_raster_url)
            emissions_gdf = traffic_emissions(road_gdf=road_gdf, aoi_poly=aoi, built_raster_url=self.built_raster_url)
        emissions_gdf_with_yearly_emissions, emission_sums = get_emission_sums(emissions_gdf)
        mean_df = get_district_summaries(emissions_gdf_with_yearly_emissions, aoi, self.ohsome)

        artifacts = []
        traffic_volume_artifact = build_traffic_volume_artifact(road_gdf, resources)
        artifacts.append(traffic_volume_artifact)
        emission_artifacts = get_emission_artifacts(emissions_gdf, resources)
        artifacts.extend(emission_artifacts)
        if mean_df is not None:
            emission_chart_artifacts = get_emission_chart_artifacts(mean_df, aoi_properties, emission_sums, resources)
            artifacts.extend(emission_chart_artifacts)

        return artifacts

    @staticmethod
    def check_aoi(aoi: shapely.MultiPolygon, aoi_properties: AoiProperties) -> None:
        germany = gpd.read_file('resources/germany_buffered_boundaries.json')
        inside_germany = aoi.within(germany.geometry)
        if not inside_germany[0]:
            raise ClimatoologyUserError(
                f'For now, estimates of traffic emissions are only available for Germany. {aoi_properties.name} is '
                'outside Germany. We are working on expanding the tool to other countries'
            )
