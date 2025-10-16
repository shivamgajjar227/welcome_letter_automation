from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    api_title: str = "Automation Task API"
    api_version: str = "0.1.0"

    celery_default_queue: str = Field("automation", env="CELERY_DEFAULT_QUEUE")

    monday_enabled: bool = Field(True, env="MONDAY_ENABLED")
    pr_site_enabled: bool = Field(False, env="PR_SITE_ENABLED")
    quickcap_enabled: bool = Field(False, env="QUICKCAP_ENABLED")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

