from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tg_source_radar"
    redis_url: str = "redis://localhost:6379/0"

    routerai_api_key: str = ""
    routerai_base_url: str = "https://routerai.ru/api/v1"
    routerai_model: str = "gpt-4o-mini"

    telethon_api_id: int = 0
    telethon_api_hash: str = ""
    telethon_session_string: str = ""

    supabase_url: str = ""
    supabase_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
