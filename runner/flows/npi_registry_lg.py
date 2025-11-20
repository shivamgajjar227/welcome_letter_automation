from __future__ import annotations

import logging
import datetime as _dt
from typing import Optional
from uuid import uuid4
from pages.monday_lg_page import MondayLGPage
from selenium.webdriver.remote.webdriver import WebDriver
from pages.pr_site_lg_page import PRSiteLG
from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import (
    post_webhook,
    post_create_task_units,
    post_update_state_task_units,
    post_micro_update_task_units,
)
from monitoring import events
from taskunits.wla_npi import NpiWlaTU

logger = logging.getLogger(__name__)


def _get_credential(metadata: RunnerMetadata) -> CredentialRef:
    candidates = [
        metadata.credentials.get(StageName.NPI_REGISTRY_LG.value),
        metadata.credentials.get("npi_registry_lg"),
    ]
    for cred in candidates:
        if cred:
            return cred
    raise RuntimeError("Monday credentials not supplied in RunnerMetadata")


def _get_base_url(metadata: RunnerMetadata) -> str:
    candidates = [
        metadata.base_urls.get(StageName.NPI_REGISTRY_LG.value),
        metadata.base_urls.get("npi_registry_lg"),
        "https://npiregistry.cms.hhs.gov/",
    ]
    for url in candidates:
        if url:
            return url
    raise RuntimeError("Monday base URL not configured")

def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    """
    Stage for testing Monday.com login and opening Welcome Letter QC board.
    """
    stage_result = StageResult(stage=StageName.NPI_REGISTRY_LG)
    stage_run_id = uuid4().hex
    stage_started_at = _dt.datetime.now(_dt.timezone.utc)

    events.emit_stage_event(
        task_id=metadata.task_id,
        stage=StageName.NPI_REGISTRY_LG,
        event="stage_started",
        status="in_progress",
        stage_run_id=stage_run_id,
        started_at=stage_started_at.isoformat(),
    )

    # cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)

    structured_log(logger, "stage_start", stage=StageName.NPI_REGISTRY_LG.value, task_id=metadata.task_id, url=base_url)

    # prsite = PRSiteLG(driver)
    driver.get(base_url)

    try:
        structured_log(logger, "step_start", stage=StageName.NPI_REGISTRY_LG.value, task_id=metadata.task_id, step="login")
        login_artifact = artifacts.capture_screenshot(driver, metadata, StageName.NPI_REGISTRY_LG, "after_login")
        stage_result.artifacts.append(login_artifact)
        structured_log(
            logger,
            "step_complete",
            stage=StageName.NPI_REGISTRY_LG.value,
            task_id=metadata.task_id,
            step="login",
            artifact_path=login_artifact.path,
        )

        structured_log(logger, "step_start", stage=StageName.NPI_REGISTRY_LG.value, task_id=metadata.task_id, step="open_board")
        board_artifact = artifacts.capture_screenshot(driver, metadata, StageName.NPI_REGISTRY_LG, "board_loaded")
        stage_result.artifacts.append(board_artifact)
        structured_log(
            logger,
            "step_complete",
            stage=StageName.NPI_REGISTRY_LG.value,
            task_id=metadata.task_id,
            step="open_board",
            artifact_path=board_artifact.path,
        )

        stage_result.mark_finished(success=True)

    except Exception as exc:
        structured_log(
            logger,
            "stage_failure",
            stage=StageName.NPI_REGISTRY_LG.value,
            task_id=metadata.task_id,
            error=str(exc)
        )
        failure_screenshot = artifacts.capture_screenshot(driver, metadata, StageName.NPI_REGISTRY_LG, "failure")
        stage_result.artifacts.append(failure_screenshot)
        stage_result.mark_finished(success=False, error=str(exc))
        raise exc

    finally:
        finished_at = _dt.datetime.now(_dt.timezone.utc)
        artifact_refs = events.upload_artifacts(
            task_id=metadata.task_id,
            stage=StageName.NPI_REGISTRY_LG,
            artifacts=stage_result.artifacts,
        )
        events.emit_stage_event(
            task_id=metadata.task_id,
            stage=StageName.NPI_REGISTRY_LG,
            event="stage_completed",
            status="completed" if stage_result.success else "failed",
            stage_run_id=stage_run_id,
            started_at=stage_started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
            artifacts=artifact_refs,
        )

    return stage_result