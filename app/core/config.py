"""Settings loaded from environment / .env (Pydantic BaseSettings)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MedSignal API"
    environment: str = "local"
    cors_origins: str = "http://localhost:5173"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    mongo_uri: str = "mongodb://localhost:27017/?directConnection=true"
    mongo_db: str = "medsignal"

    redis_url: str = "redis://localhost:6379/0"
    redis_sentinels: str = ""  # "host1:26379,host2:26379,host3:26379"
    redis_master_name: str = "mymaster"

    openfda_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
