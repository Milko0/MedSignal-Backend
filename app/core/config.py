from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings from environment variables and .env.

    MERGE NOTE: keep your existing variables (Mongo, Redis, Sentinel). The new ones are
    STORAGE_BACKEND, DATA_DIR, CACHE_DIR and the external client limits.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MedSignal API"
    environment: str = "local"
    cors_origins: str = "http://localhost:5173"

    # "memory" = JSON Lines files in DATA_DIR (reference adapters); "databases" = Mongo + Redis (teammates)
    storage_backend: str = "memory"
    data_dir: str = "data/clean"
    cache_dir: str = "data/cache"

    mongo_uri: str = "mongodb://localhost:27017/?directConnection=true"
    mongo_db: str = "medsignal"
    redis_url: str = "redis://localhost:6379/0"
    redis_sentinels: str = ""
    redis_master_name: str = "mymaster"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    openfda_base_url: str = "https://api.fda.gov"
    openfda_api_key: str | None = None
    rxnorm_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    dailymed_base_url: str = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
    http_timeout_seconds: float = 60.0
    http_max_retries: int = 4
    rxnorm_requests_per_second: float = 8.0   # RxNav allows 20/s; stay well below
    openfda_requests_per_second: float = 2.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
