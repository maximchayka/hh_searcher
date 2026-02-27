import json

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = "change-me"
    DEBUG: bool = False

    # Declared as str so pydantic-settings does NOT attempt json.loads() on it.
    # pydantic-settings v2 calls json.loads() only for complex types (list/dict).
    # The env var is still named ALLOWED_ORIGINS (via validation_alias).
    ALLOWED_ORIGINS_STR: str = Field(
        default="http://localhost:3000",
        validation_alias="ALLOWED_ORIGINS",
    )

    @computed_field  # type: ignore[misc]
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        v = self.ALLOWED_ORIGINS_STR.strip()
        if not v:
            return ["http://localhost:3000"]
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(u) for u in parsed]
        except (ValueError, TypeError):
            pass
        return [u.strip() for u in v.split(",") if u.strip()]

    DATABASE_URL: str = "postgresql+asyncpg://jobautoapply:jobautoapply@db:5432/jobautoapply"

    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    HH_CLIENT_ID: str = ""
    HH_CLIENT_SECRET: str = ""
    HH_REDIRECT_URI: str = "http://localhost:3000/auth/hh/callback"
    HH_API_BASE_URL: str = "https://api.hh.ru"

    OPENAI_API_KEY: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days


settings = Settings()
