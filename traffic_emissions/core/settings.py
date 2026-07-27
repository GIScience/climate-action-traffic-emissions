from typing import Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_s3_access_key: str
    data_s3_secret_key: SecretStr
    data_s3_endpoint: str
    data_s3_bucket_name: str
    pop_raster_object_name: str
    built_raster_object_name: str

    feature_flag_ohsome2: bool = False
    ohsome_base_url: Optional[str] = None

    model_config = SettingsConfigDict(env_file='.env')  # dead: disable
