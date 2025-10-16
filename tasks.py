"""
Celery task definitions for the reusable headless Selenium runner.

This module is responsible for:
  * Building :class:`runner.context.RunnerMetadata` objects from environment
    configuration.
  * Calling :func:`runner.headless_runner.run_headless_flow` for each stage.
  * Providing a synchronous CLI entry point used by docker-compose.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

from celery import Celery

from runner.context import CredentialRef, RunnerMetadata, StageConfig, StageName
from runner.headless_runner import run_headless_flow
import task_tracking

# ------------------------------------------------------------------------------
# Celery application setup
# ------------------------------------------------------------------------------

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery("welcome_letter_automation", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

LOG_LEVEL = os.getenv("TASKS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("tasks")

# ------------------------------------------------------------------------------
# Metadata builders
# ------------------------------------------------------------------------------


def _get_env(name: str, *, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Environment variable '{name}' is required")
    return value


def build_metadata(enabled_stages: Iterable[StageName]) -> RunnerMetadata:
    stages = list(enabled_stages)
    stage_config: Dict[StageName, StageConfig] = {}
    credentials: Dict[str, CredentialRef] = {}
    base_urls: Dict[str, str] = {}

    def register_stage(stage: StageName, user_env: str, pass_env: str, url_env: str, default_url: str) -> None:
        username = _get_env(user_env)
        password = _get_env(pass_env)
        if username and password:
            credentials[stage.value] = CredentialRef(username=username, password=password)
            base_urls[stage.value] = _get_env(url_env, default=default_url) or default_url
            stage_config[stage] = StageConfig(enabled=True)
        else:
            stage_config[stage] = StageConfig(enabled=False)
            logger.warning("Disabling stage %s due to missing credentials", stage.value)

    requested = set(stages)

    for stage in StageName:
        if stage not in requested:
            stage_config[stage] = StageConfig(enabled=False)
            continue

        if stage == StageName.MONDAY:
            register_stage(stage, "MONDAY_USERNAME", "MONDAY_PASSWORD", "MONDAY_BASE_URL", "https://pns-mgmt.monday.com/")
        elif stage == StageName.PR_SITE:
            register_stage(stage, "PR_SITE_USERNAME", "PR_SITE_PASSWORD", "PR_SITE_BASE_URL", "https://pss.ad.pns-mgmt.com/ProvPractice.aspx#s1")
        elif stage == StageName.QUICKCAP:
            register_stage(stage, "QUICKCAP_USERNAME", "QUICKCAP_PASSWORD", "QUICKCAP_BASE_URL", "https://pnstest.quickcap.net")
        else:
            stage_config[stage] = StageConfig(enabled=False)

    selenium_url = _get_env("SELENIUM_URL")
    media_root = _get_env("MEDIA_ROOT", default="media") or "media"
    log_root = _get_env("LOG_ROOT", default="app_logs") or "app_logs"

    metadata = RunnerMetadata(
        selenium_url=selenium_url,
        media_root=media_root,
        log_root=log_root,
        base_urls=base_urls,
        credentials=credentials,
        stage_config=stage_config,
    )

    return metadata


def _ensure_stage_enabled(metadata: RunnerMetadata, stage: StageName) -> None:
    cfg = metadata.stage_config.get(stage)
    if not cfg or not cfg.enabled:
        raise RuntimeError(f"Stage '{stage.value}' is disabled due to missing configuration")


# ------------------------------------------------------------------------------
# Celery tasks
# ------------------------------------------------------------------------------

@celery_app.task(name="tasks.run_monday")
def run_monday(task_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> dict:
    """Execute only the Monday ingestion stage."""
    metadata = build_metadata(enabled_stages=[StageName.MONDAY])
    _ensure_stage_enabled(metadata, StageName.MONDAY)
    if task_id:
        metadata.task_id = task_id
    if payload:
        metadata.request_payload = payload
    task_tracking.update_task_status(task_id or metadata.task_id, "in_progress", attempt_delta=1)
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        task_tracking.update_task_status(
            task_id or metadata.task_id,
            "failed",
            message=str(exc),
        )
        raise

    stage = result.stages.get(StageName.MONDAY)
    task_tracking.update_task_status(
        task_id or result.task_id,
        "completed" if stage and stage.success else "failed",
        result={"monday": stage.data if stage else {}},
    )
    return {
        "task_id": result.task_id,
        "success": bool(stage and stage.success),
        "artifacts": [artifact.__dict__ for artifact in stage.artifacts] if stage else [],
        "data": stage.data if stage else {},
    }


@celery_app.task(name="tasks.run_pr_site")
def run_pr_site(task_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> dict:
    """Execute only the PR Site enrichment stage."""
    metadata = build_metadata(enabled_stages=[StageName.PR_SITE])
    _ensure_stage_enabled(metadata, StageName.PR_SITE)
    if task_id:
        metadata.task_id = task_id
    if payload:
        metadata.request_payload = payload
    task_tracking.update_task_status(task_id or metadata.task_id, "in_progress", attempt_delta=1)
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        task_tracking.update_task_status(
            task_id or metadata.task_id,
            "failed",
            message=str(exc),
        )
        raise
    stage = result.stages.get(StageName.PR_SITE)
    task_tracking.update_task_status(
        task_id or result.task_id,
        "completed" if stage and stage.success else "failed",
        result={"pr_site": stage.data if stage else {}},
    )
    return {
        "task_id": result.task_id,
        "success": bool(stage and stage.success),
        "artifacts": [artifact.__dict__ for artifact in stage.artifacts] if stage else [],
        "data": stage.data if stage else {},
    }


@celery_app.task(name="tasks.run_quickcap")
def run_quickcap(task_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> dict:
    """Execute only the QuickCap stage."""
    metadata = build_metadata(enabled_stages=[StageName.QUICKCAP])
    _ensure_stage_enabled(metadata, StageName.QUICKCAP)
    if task_id:
        metadata.task_id = task_id
    if payload:
        metadata.request_payload = payload
    task_tracking.update_task_status(task_id or metadata.task_id, "in_progress", attempt_delta=1)
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        task_tracking.update_task_status(
            task_id or metadata.task_id,
            "failed",
            message=str(exc),
        )
        raise
    stage = result.stages.get(StageName.QUICKCAP)
    task_tracking.update_task_status(
        task_id or result.task_id,
        "completed" if stage and stage.success else "failed",
        result={"quickcap": stage.data if stage else {}},
    )
    return {
        "task_id": result.task_id,
        "success": bool(stage and stage.success),
        "artifacts": [artifact.__dict__ for artifact in stage.artifacts] if stage else [],
        "data": stage.data if stage else {},
    }


@celery_app.task(name="tasks.run_pipeline")
def run_pipeline(task_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> dict:
    """
    Execute the full pipeline. Stages without credentials are skipped automatically.
    """
    metadata = build_metadata(enabled_stages=list(StageName))
    if task_id:
        metadata.task_id = task_id
    if payload:
        metadata.request_payload = payload
    task_tracking.update_task_status(task_id or metadata.task_id, "in_progress", attempt_delta=1)
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        task_tracking.update_task_status(
            task_id or metadata.task_id,
            "failed",
            message=str(exc),
        )
        raise
    task_tracking.update_task_status(
        task_id or result.task_id,
        "completed" if result.success else "failed",
        result={stage.value: stage_result.data for stage, stage_result in result.stages.items()},
    )
    return {
        "task_id": result.task_id,
        "success": result.success,
        "stages": {
            stage.value: {
                "success": record.success,
                "error": record.error,
                "artifacts": [artifact.__dict__ for artifact in record.artifacts],
                "data": record.data,
            }
            for stage, record in result.stages.items()
        },
    }


# ------------------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------------------

def main() -> int:
    """
    Run the pipeline synchronously. Intended for docker-compose `test-runner`.
    """
    try:
        summary = run_pipeline()
    except Exception:  # pragma: no cover - depends on external systems
        logger.exception("Pipeline execution failed")
        return 1

    logger.info("Pipeline summary: %s", summary)
    return 0 if summary.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
