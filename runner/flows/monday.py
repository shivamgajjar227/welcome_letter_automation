"""
Headless runner implementation for the Monday.com ingestion stage.
"""

from __future__ import annotations

import logging
import datetime as _dt
from typing import Optional
from uuid import uuid4

from selenium.webdriver.remote.webdriver import WebDriver
from pages.monday_page import MondayPage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook
from monitoring import events

logger = logging.getLogger(__name__)


def _get_credential(metadata: RunnerMetadata) -> CredentialRef:
    candidates = [
        metadata.credentials.get(StageName.MONDAY.value),
        metadata.credentials.get("monday"),
    ]
    for cred in candidates:
        if cred:
            return cred
    raise RuntimeError("Monday credentials not supplied in RunnerMetadata")


def _get_base_url(metadata: RunnerMetadata) -> str:
    candidates = [
        metadata.base_urls.get(StageName.MONDAY.value),
        metadata.base_urls.get("monday"),
        "https://pns-mgmt.monday.com/",
    ]
    for url in candidates:
        if url:
            return url
    raise RuntimeError("Monday base URL not configured")


def _send_records_to_api(npis, metadata: RunnerMetadata) -> None:
    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.MONDAY.value,
        "records": npis,
    }
    if not post_webhook(metadata, StageName.MONDAY, payload):
        structured_log(
            logger,
            "webhook_missing",
            stage=StageName.MONDAY.value,
            task_id=metadata.task_id,
        )


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    """
    Execute the Monday.com ingestion stage.

    Steps:
        1. Navigate to Monday board and authenticate.
        2. Collect NPIs in "Not Started" state.
        3. Insert fresh rows into `pr_site_data` with status=0.
        4. Capture artifacts (screenshot + JSON dump).
    """
    stage_result = StageResult(stage=StageName.MONDAY)
    stage_run_id = uuid4().hex
    stage_started_at = _dt.datetime.now(_dt.timezone.utc)
    events.emit_stage_event(
        task_id=metadata.task_id,
        stage=StageName.MONDAY,
        event="stage_started",
        status="in_progress",
        stage_run_id=stage_run_id,
        started_at=stage_started_at.isoformat(),
    )

    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)

    structured_log(logger, "stage_start", stage=StageName.MONDAY.value, task_id=metadata.task_id, url=base_url)

    monday_page = MondayPage(driver)
    driver.get(base_url)

    try:
        # 1. Authenticate (only when the login form is present)
        structured_log(logger, "step_start", stage=StageName.MONDAY.value, task_id=metadata.task_id, step="login")
        if monday_page.is_login_page():
            monday_page.login(cred.username, cred.password)
        else:
            structured_log(
                logger,
                "login_skipped",
                stage=StageName.MONDAY.value,
                task_id=metadata.task_id,
            )
        login_artifact = artifacts.capture_screenshot(driver, metadata, StageName.MONDAY, "after_login")
        stage_result.artifacts.append(login_artifact)
        structured_log(
            logger,
            "step_complete",
            stage=StageName.MONDAY.value,
            task_id=metadata.task_id,
            step="login",
            artifact_path=login_artifact.path,
        )

        # 2. Navigate to the target board
        structured_log(logger, "step_start", stage=StageName.MONDAY.value, task_id=metadata.task_id, step="open_board")
        monday_page.click_welcome_letter_qc()
        board_artifact = artifacts.capture_screenshot(driver, metadata, StageName.MONDAY, "board_loaded")
        stage_result.artifacts.append(board_artifact)
        structured_log(
            logger,
            "step_complete",
            stage=StageName.MONDAY.value,
            task_id=metadata.task_id,
            step="open_board",
            artifact_path=board_artifact.path,
        )

        # 3. Collect NPIs currently marked as "Not Started"
        structured_log(
            logger,
            "step_start",
            stage=StageName.MONDAY.value,
            task_id=metadata.task_id,
            step="collect_npis",
        )
        pre_collect_artifact = artifacts.capture_screenshot(driver, metadata, StageName.MONDAY, "before_collect_npis")
        stage_result.artifacts.append(pre_collect_artifact)
        npis = monday_page.get_pr_site_npis()
        for record in npis:
            health_plan = str(record.get("health_plan", "")).strip().lower()
            if health_plan in ["doctors", "doctor health"]:
                record["health_plan"] = "Doctors Healthcare"
                record["lines_of_business"] = "Doctors Healthcare"
        structured_log(
            logger,
            "npis_collected",
            task_id=metadata.task_id,
            count=len(npis),
            sample=npis[:3] if npis else [],
        )

        npis_dom_artifact = artifacts.capture_dom(driver, metadata, StageName.MONDAY, "npis_table")
        stage_result.artifacts.append(npis_dom_artifact)

        artifact = artifacts.capture_json(npis, metadata, StageName.MONDAY, "npis")
        stage_result.artifacts.append(artifact)

        if not npis:
            structured_log(logger, "no_records_found", stage=StageName.MONDAY.value, task_id=metadata.task_id)
            stage_result.data["npi_records"] = []
            stage_result.mark_finished(success=True)
            finished_at = _dt.datetime.now(_dt.timezone.utc)
            artifact_refs = events.upload_artifacts(
                task_id=metadata.task_id,
                stage=StageName.MONDAY,
                artifacts=stage_result.artifacts,
            )
            events.emit_stage_event(
                task_id=metadata.task_id,
                stage=StageName.MONDAY,
                event="stage_completed",
                status="completed",
                stage_run_id=stage_run_id,
                started_at=stage_started_at.isoformat(),
                finished_at=finished_at.isoformat(),
                duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
                summary={"records_total": 0, "records_success": 0, "records_failed": 0},
                artifacts=artifact_refs,
            )
            return stage_result

        # 4. Send NPIs to external API for persistence
        _send_records_to_api(npis, metadata)

        structured_log(
            logger,
            "step_complete",
            stage=StageName.MONDAY.value,
            task_id=metadata.task_id,
            step="collect_npis",
            artifact_path=artifact.path,
        )

        stage_result.data["npi_records"] = npis
        stage_result.mark_finished(success=True)
    except Exception as exc:  # pragma: no cover - requires live systems
        structured_log(
            logger,
            "stage_failure",
            stage=StageName.MONDAY.value,
            task_id=metadata.task_id,
            error=str(exc),
        )
        failure_screenshot = artifacts.capture_screenshot(driver, metadata, StageName.MONDAY, "failure")
        failure_dom = artifacts.capture_dom(driver, metadata, StageName.MONDAY, "failure")
        stage_result.artifacts.extend([failure_screenshot, failure_dom])
        stage_result.mark_finished(success=False, error=str(exc))
        finished_at = _dt.datetime.now(_dt.timezone.utc)
        artifact_refs = events.upload_artifacts(
            task_id=metadata.task_id,
            stage=StageName.MONDAY,
            artifacts=stage_result.artifacts,
        )
        events.emit_stage_event(
            task_id=metadata.task_id,
            stage=StageName.MONDAY,
            event="stage_failed",
            status="failed",
            stage_run_id=stage_run_id,
            started_at=stage_started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
            message=str(exc),
            artifacts=artifact_refs,
        )
        return stage_result

    finished_at = _dt.datetime.now(_dt.timezone.utc)
    artifact_refs = events.upload_artifacts(
        task_id=metadata.task_id,
        stage=StageName.MONDAY,
        artifacts=stage_result.artifacts,
    )
    records = stage_result.data.get("npi_records", [])
    summary = {
        "records_total": len(records),
        "records_success": len(records),
        "records_failed": 0,
    }
    events.emit_stage_event(
        task_id=metadata.task_id,
        stage=StageName.MONDAY,
        event="stage_completed",
        status="completed",
        stage_run_id=stage_run_id,
        started_at=stage_started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
        summary=summary,
        artifacts=artifact_refs,
    )

    for index, record in enumerate(records, start=1):
        npi_value = str(record.get("npi_number") or record.get("npi") or record.get("id") or "")
        if not npi_value:
            continue
        events.emit_npi_event(
            task_id=metadata.task_id,
            stage=StageName.MONDAY,
            npi=npi_value,
            status="completed",
            attempt=int(record.get("attempt", 1) or 1),
            stage_run_id=stage_run_id,
            input_snapshot=record,
            output_snapshot={"queued": True, "position": index},
            artifacts=artifact_refs,
        )

    return stage_result
