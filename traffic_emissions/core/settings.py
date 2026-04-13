from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_s3_access_key: str
    data_s3_secret_key: SecretStr
    data_s3_endpoint: str
    data_s3_bucket_name: str
    pop_raster_object_name: str
    built_raster_object_name: str

    model_config = SettingsConfigDict(env_file='.env')  # dead: disable
