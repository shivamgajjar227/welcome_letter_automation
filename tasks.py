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
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional

from celery import Celery
import requests
from requests import RequestException

from config import get_settings
from runner.context import CredentialRef, RunnerMetadata, StageConfig, StageName
from runner.headless_runner import run_headless_flow

# ------------------------------------------------------------------------------
# Celery application setup
# ------------------------------------------------------------------------------

settings = get_settings()

BROKER_URL = settings.celery_broker_url
RESULT_BACKEND = settings.celery_result_backend

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

LOG_LEVEL = settings.tasks_log_level.upper()


def configure_logging() -> logging.Logger:
    worker_name = os.getenv("CELERY_WORKER_NAME", "celery-worker")
    logging.basicConfig(
        level=LOG_LEVEL,
        format=f"%(asctime)s %(levelname)s [{worker_name}:%(name)s] %(message)s",
    )
    return logging.getLogger("tasks")


logger = configure_logging()


def send_status_update(
    task_id: str,
    status: str,
    *,
    stage: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
) -> None:
    webhook = settings.task_status_webhook_url
    if not webhook:
        logger.debug("Task %s status %s (no webhook configured)", task_id, status)
        return

    payload: Dict[str, Any] = {
        "task_id": task_id,
        "status": status,
    }
    if stage:
        payload["stage"] = stage
    if result is not None:
        payload["result"] = result
    if message:
        payload["message"] = message

    try:
        response = requests.post(webhook, json=payload, timeout=30)
        response.raise_for_status()
    except RequestException as exc:
        logger.warning("Failed to send task status update: %s", exc)

# ------------------------------------------------------------------------------
# Metadata builders
# ------------------------------------------------------------------------------


def build_metadata(enabled_stages: Iterable[StageName]) -> RunnerMetadata:
    stages = list(enabled_stages)
    stage_config: Dict[StageName, StageConfig] = {}
    credentials: Dict[str, CredentialRef] = {}
    base_urls: Dict[str, str] = {}

    stage_credentials = {
        StageName.MONDAY: (
            settings.monday_username,
            settings.monday_password,
            settings.monday_base_url,
        ),
        StageName.PR_SITE: (
            settings.pr_site_username,
            settings.pr_site_password,
            settings.pr_site_base_url,
        ),
        StageName.QUICKCAP: (
            settings.quickcap_username,
            settings.quickcap_password,
            settings.quickcap_base_url,
        ),
    }
    stage_toggles = {
        StageName.MONDAY: settings.monday_enabled,
        StageName.PR_SITE: settings.pr_site_enabled,
        StageName.QUICKCAP: settings.quickcap_enabled,
    }

    def register_stage(stage: StageName) -> None:
        if not stage_toggles.get(stage, True):
            stage_config[stage] = StageConfig(enabled=False)
            logger.info("Stage %s disabled via configuration toggle", stage.value)
            return
        username, password, default_url = stage_credentials.get(stage, (None, None, None))
        if username and password:
            credentials[stage.value] = CredentialRef(username=username, password=password)
            base_urls[stage.value] = default_url
            cfg = StageConfig(enabled=True)
            if stage == StageName.MONDAY and settings.monday_ingest_api_url:
                cfg.extra["webhook_url"] = settings.monday_ingest_api_url
            stage_config[stage] = cfg
        else:
            stage_config[stage] = StageConfig(enabled=False)
            logger.warning("Disabling stage %s due to missing credentials", stage.value)

    requested = set(stages)

    for stage in StageName:
        if stage not in requested:
            stage_config[stage] = StageConfig(enabled=False)
            continue

        register_stage(stage)

    selenium_url = settings.selenium_url
    media_root = settings.media_root or "media"
    log_root = settings.log_root or "app_logs"

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
    current_task_id = task_id or metadata.task_id
    send_status_update(
        current_task_id,
        "in_progress",
        stage=StageName.MONDAY.value,
    )
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        send_status_update(
            current_task_id,
            "failed",
            stage=StageName.MONDAY.value,
            message=str(exc),
        )
        raise

    stage = result.stages.get(StageName.MONDAY)
    artifacts = [asdict(artifact) for artifact in stage.artifacts] if stage else []
    send_status_update(
        current_task_id,
        "completed" if stage and stage.success else "failed",
        stage=StageName.MONDAY.value,
        result={
            "data": stage.data if stage else {},
            "artifacts": artifacts,
        },
    )
    return {
        "task_id": result.task_id,
        "success": bool(stage and stage.success),
        "artifacts": artifacts,
        "data": stage.data if stage else {},
    }


@celery_app.task(name="tasks.run_monday_status")
def run_monday_status(task_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> dict:
    """Execute the Monday board status update stage."""
    metadata = build_metadata(enabled_stages=[StageName.MONDAY_STATUS])
    _ensure_stage_enabled(metadata, StageName.MONDAY_STATUS)
    if task_id:
        metadata.task_id = task_id
    if payload:
        metadata.request_payload = payload
    current_task_id = task_id or metadata.task_id
    send_status_update(
        current_task_id,
        "in_progress",
        stage=StageName.MONDAY_STATUS.value,
    )
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        send_status_update(
            current_task_id,
            "failed",
            stage=StageName.MONDAY_STATUS.value,
            message=str(exc),
        )
        raise

    stage = result.stages.get(StageName.MONDAY_STATUS)
    artifacts = [asdict(artifact) for artifact in stage.artifacts] if stage else []
    send_status_update(
        current_task_id,
        "completed" if stage and stage.success else "failed",
        stage=StageName.MONDAY_STATUS.value,
        result={
            "data": stage.data if stage else {},
            "artifacts": artifacts,
        },
    )
    return {
        "task_id": result.task_id,
        "success": bool(stage and stage.success),
        "artifacts": artifacts,
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
    current_task_id = task_id or metadata.task_id
    send_status_update(
        current_task_id,
        "in_progress",
        stage=StageName.PR_SITE.value,
    )
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        send_status_update(
            current_task_id,
            "failed",
            stage=StageName.PR_SITE.value,
            message=str(exc),
        )
        raise
    stage = result.stages.get(StageName.PR_SITE)
    artifacts = [asdict(artifact) for artifact in stage.artifacts] if stage else []
    send_status_update(
        current_task_id,
        "completed" if stage and stage.success else "failed",
        stage=StageName.PR_SITE.value,
        result={
            "data": stage.data if stage else {},
            "artifacts": artifacts,
        },
    )
    return {
        "task_id": result.task_id,
        "success": bool(stage and stage.success),
        "artifacts": artifacts,
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
    current_task_id = task_id or metadata.task_id
    send_status_update(
        current_task_id,
        "in_progress",
        stage=StageName.QUICKCAP.value,
    )
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        send_status_update(
            current_task_id,
            "failed",
            stage=StageName.QUICKCAP.value,
            message=str(exc),
        )
        raise
    stage = result.stages.get(StageName.QUICKCAP)
    artifacts = [asdict(artifact) for artifact in stage.artifacts] if stage else []
    send_status_update(
        current_task_id,
        "completed" if stage and stage.success else "failed",
        stage=StageName.QUICKCAP.value,
        result={
            "data": stage.data if stage else {},
            "artifacts": artifacts,
        },
    )
    return {
        "task_id": result.task_id,
        "success": bool(stage and stage.success),
        "artifacts": artifacts,
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
    current_task_id = task_id or metadata.task_id
    send_status_update(current_task_id, "in_progress")
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        send_status_update(current_task_id, "failed", message=str(exc))
        raise
    send_status_update(
        current_task_id,
        "completed" if result.success else "failed",
        result={
            stage.value: {
                "data": stage_result.data,
                "artifacts": [asdict(artifact) for artifact in stage_result.artifacts],
                "success": stage_result.success,
                "error": stage_result.error,
            }
            for stage, stage_result in result.stages.items()
        },
    )
    return {
        "task_id": result.task_id,
        "success": result.success,
        "stages": {
            stage.value: {
                "success": record.success,
                "error": record.error,
                "artifacts": [asdict(artifact) for artifact in record.artifacts],
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
