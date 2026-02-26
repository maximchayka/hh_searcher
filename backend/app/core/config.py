import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = "change-me"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        v = v.strip()
        if not v:
            return ["http://localhost:3000"]
        # Try JSON array: ["url1","url2"]
        if v.startswith("["):
            return json.loads(v)
        # Otherwise comma-separated plain URLs
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
