from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openrouter_http_referer: Optional[str] = None
    openrouter_app_name: str = "amazon-auto-select"
    amazon_api_provider: str = "mock"
    serpapi_key: Optional[str] = None
    rainforest_api_key: Optional[str] = None
    keepa_api_key: Optional[str] = None
    feishu_webhook_url: Optional[str] = None
    database_url: str = "sqlite:///./amazon_test.db"
    daily_run_hour: int = 8
    openai_model: str = "gpt-4o-mini"
    amazon_ads_api_enabled: bool = False
    default_ad_test_cost: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
