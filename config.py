from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse
from pathlib import Path

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
    celery_broker_url: str = Field("redis://localhost:10008/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:10008/1", env="CELERY_RESULT_BACKEND")

    tasks_log_level: str = Field("INFO", env="TASKS_LOG_LEVEL")

    monday_username: Optional[str] = Field("autoprocess@pns-mgmt.com", env="MONDAY_USERNAME")
    monday_password: Optional[str] = Field("@VEnger200@@@@", env="MONDAY_PASSWORD")
    monday_base_url: str = Field("https://pns-mgmt.monday.com/", env="MONDAY_BASE_URL")

    pr_site_username: Optional[str] = Field("autoprocess@ad.pns-mgmt.com", env="PR_SITE_USERNAME")
    pr_site_password: Optional[str] = Field("P%23194714496192ab", env="PR_SITE_PASSWORD")
    pr_site_base_url: str = Field(
        "https://pss.ad.pns-mgmt.com/ProvPractice.aspx#s1", env="PR_SITE_BASE_URL"
    )
    pr_site_login_url: Optional[str] = Field(None, env="PR_SITE_LOGIN_URL")

    quickcap_username: Optional[str] = Field("autoprocess@pns-mgmt.com", env="QUICKCAP_USERNAME")
    quickcap_password: Optional[str] = Field("Pns@#111125", env="QUICKCAP_PASSWORD")
    quickcap_base_url: str = Field("https://pnstest.quickcap.net", env="QUICKCAP_BASE_URL")

    selenium_url: Optional[str] = Field(None, env="SELENIUM_URL")
    media_root: str = Field("media", env="MEDIA_ROOT")
    log_root: str = Field("app_logs", env="LOG_ROOT")
    selenium_headless: bool = Field(True, env="SELENIUM_HEADLESS")
    monday_ingest_api_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/monday", env="MONDAY_INGEST_API_URL")
    monday_status_api_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/monday-status", env="MONDAY_STATUS_API_URL")
    monday_status_fetch_api_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/data/monday-status", env="MONDAY_STATUS_FETCH_API_URL")
    task_status_webhook_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/task-status", env="TASK_STATUS_WEBHOOK_URL")
    pr_site_ingest_api_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/pr-site", env="PR_SITE_INGEST_API_URL")
    pr_site_fetch_api_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/data/pr-site", env="PR_SITE_FETCH_API_URL")
    quickcap_ingest_api_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/quickcap", env="QUICKCAP_INGEST_API_URL")
    quickcap_fetch_api_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/data/quickcap", env="QUICKCAP_FETCH_API_URL")
    stage_events_webhook_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/stage-events", env="STAGE_EVENTS_WEBHOOK_URL")
    npi_events_webhook_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/npi-events", env="NPI_EVENTS_WEBHOOK_URL")
    artifact_events_webhook_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/artifacts", env="ARTIFACT_EVENTS_WEBHOOK_URL")
    pipeline_events_webhook_url: Optional[str] = Field("http://0.0.0.0:10022/api/automation/webhooks/pipeline-events", env="PIPELINE_EVENTS_WEBHOOK_URL")
    artifact_base_url: Optional[str] = Field(None, env="ARTIFACT_BASE_URL")

    db_user: str = Field("dbroot", env="DB_USER")
    db_password: str = Field("dbroot", env="DB_PASSWORD")
    db_host: str = Field("127.0.0.1", env="DB_HOST")
    db_port: int = Field(3306, env="DB_PORT")
    db_name: str = Field("test_db", env="DB_NAME")
    remote_db_tunnel: bool = Field(False, env="REMOTE_DB_TUNNEL")

    monday_enabled: bool = Field(True, env="MONDAY_ENABLED")
    monday_status_enabled: bool = Field(True, env="MONDAY_STATUS_ENABLED")
    pr_site_enabled: bool = Field(True, env="PR_SITE_ENABLED")
    quickcap_enabled: bool = Field(True, env="QUICKCAP_ENABLED")

    auth_client_id: Optional[str] = Field(None, env="AUTH_CLIENT_ID")
    auth_client_secret: Optional[str] = Field(None, env="AUTH_CLIENT_SECRET")
    auth_token_url: Optional[str] = Field(None, env="AUTH_TOKEN_URL")
    auth_token_scope: Optional[str] = Field(None, env="AUTH_TOKEN_SCOPE")
    auth_token_cache_path: Optional[str] = Field(None, env="AUTH_TOKEN_CACHE_PATH")
    auth_fixed_token: Optional[str] = Field("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNzYyNTM3MTk3fQ.vt21Q7eiXaPeW2kkMDB3ybRw1OzPu94JxBduzBOUml4", env="AUTH_TOKEN_CACHE_PATH")


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def model_post_init(self, __context: Dict[str, Any]) -> None:  # type: ignore[override]
        base_host = "127.0.0.1" if self.api_host in {"0.0.0.0", "::", "localhost"} else self.api_host
        base_url = f"http://{base_host}:{self.api_port}"

        if not self.monday_ingest_api_url:
            object.__setattr__(self, "monday_ingest_api_url", f"{base_url}/webhooks/monday")

        if not self.monday_status_api_url:
            object.__setattr__(self, "monday_status_api_url", f"{base_url}/webhooks/monday-status")
        if not self.monday_status_fetch_api_url:
            object.__setattr__(self, "monday_status_fetch_api_url", f"{base_url}/data/monday-status")

        if not self.pr_site_ingest_api_url:
            object.__setattr__(self, "pr_site_ingest_api_url", f"{base_url}/webhooks/pr-site")
        if not self.pr_site_fetch_api_url:
            object.__setattr__(self, "pr_site_fetch_api_url", f"{base_url}/data/pr-site")

        if not self.quickcap_ingest_api_url:
            object.__setattr__(self, "quickcap_ingest_api_url", f"{base_url}/webhooks/quickcap")
        if not self.quickcap_fetch_api_url:
            object.__setattr__(self, "quickcap_fetch_api_url", f"{base_url}/data/quickcap")

        if not self.auth_token_cache_path:
            cache_dir = Path(self.log_root).resolve()
            cache_dir.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self, "auth_token_cache_path", str(cache_dir / "auth_token.json"))

        if not self.task_status_webhook_url:
            object.__setattr__(self, "task_status_webhook_url", f"{base_url}/webhooks/task-status")
        if not self.stage_events_webhook_url:
            object.__setattr__(self, "stage_events_webhook_url", f"{base_url}/webhooks/stage-events")
        if not self.npi_events_webhook_url:
            object.__setattr__(self, "npi_events_webhook_url", f"{base_url}/webhooks/npi-events")
        if not self.artifact_events_webhook_url:
            object.__setattr__(self, "artifact_events_webhook_url", f"{base_url}/webhooks/artifacts")
        if not self.pipeline_events_webhook_url:
            object.__setattr__(self, "pipeline_events_webhook_url", f"{base_url}/webhooks/pipeline-events")

        if (
            not self.pr_site_login_url
            and self.pr_site_base_url
            and self.pr_site_username
            and self.pr_site_password
        ):
            normalized = self.pr_site_base_url
            if "://" not in normalized:
                normalized = f"https://{normalized}"
            parsed = urlparse(normalized)
            if parsed.username or parsed.password:
                object.__setattr__(self, "pr_site_login_url", normalized)
            elif parsed.netloc:
                auth_netloc = f"{self.pr_site_username}:{self.pr_site_password}@{parsed.netloc}"
                auth_url = urlunparse(parsed._replace(netloc=auth_netloc))
                object.__setattr__(self, "pr_site_login_url", auth_url)


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
