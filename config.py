from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralised application configuration loaded from environment variables."""

    api_title: str = "Automation Task API"
    api_version: str = "0.1.0"
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_reload: bool = Field(False, env="API_RELOAD")

    celery_default_queue: str = Field("automation", env="CELERY_DEFAULT_QUEUE")
    celery_broker_url: str = Field("redis://localhost:10080/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:10080/1", env="CELERY_RESULT_BACKEND")

    tasks_log_level: str = Field("INFO", env="TASKS_LOG_LEVEL")

    monday_username: Optional[str] = Field("autoprocess@pns-mgmt.com", env="MONDAY_USERNAME")
    monday_password: Optional[str] = Field("@VEnger200@@@@", env="MONDAY_PASSWORD")
    monday_base_url: str = Field("https://pns-mgmt.monday.com/", env="MONDAY_BASE_URL")

    pr_site_username: Optional[str] = Field(None, env="PR_SITE_USERNAME")
    pr_site_password: Optional[str] = Field(None, env="PR_SITE_PASSWORD")
    pr_site_base_url: str = Field(
        "https://pss.ad.pns-mgmt.com/ProvPractice.aspx#s1", env="PR_SITE_BASE_URL"
    )

    quickcap_username: Optional[str] = Field(None, env="QUICKCAP_USERNAME")
    quickcap_password: Optional[str] = Field(None, env="QUICKCAP_PASSWORD")
    quickcap_base_url: str = Field("https://pnstest.quickcap.net", env="QUICKCAP_BASE_URL")

    selenium_url: Optional[str] = Field(None, env="SELENIUM_URL")
    media_root: str = Field("media", env="MEDIA_ROOT")
    log_root: str = Field("app_logs", env="LOG_ROOT")

    monday_ingest_api_url: Optional[str] = Field("http://0.0.0.0:8070", env="MONDAY_INGEST_API_URL")
    task_status_webhook_url: Optional[str] = Field("http://0.0.0.0:8070", env="TASK_STATUS_WEBHOOK_URL")

    db_user: str = Field("dbroot", env="DB_USER")
    db_password: str = Field("dbroot", env="DB_PASSWORD")
    db_host: str = Field("127.0.0.1", env="DB_HOST")
    db_port: int = Field(3306, env="DB_PORT")
    db_name: str = Field("test_db", env="DB_NAME")
    remote_db_tunnel: bool = Field(False, env="REMOTE_DB_TUNNEL")

    monday_enabled: bool = Field(True, env="MONDAY_ENABLED")
    pr_site_enabled: bool = Field(False, env="PR_SITE_ENABLED")
    quickcap_enabled: bool = Field(False, env="QUICKCAP_ENABLED")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
