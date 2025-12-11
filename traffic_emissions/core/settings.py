from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_earth_engine_service_account: str
    google_earth_engine_key: str

    model_config = SettingsConfigDict(env_file='.env')  # dead: disable
