"""Headless runner implementation for updating Monday board statuses."""

from __future__ import annotations

import logging
import time
from typing import Dict, List

from selenium.webdriver.remote.webdriver import WebDriver

from pages.monday_page import MondayPage

from .. import artifacts
from ..context import RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook

logger = logging.getLogger(__name__)


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    stage_result = StageResult(stage=StageName.MONDAY_STATUS)
    records: List[Dict] = list(metadata.request_payload.get("records", []))

    structured_log(
        logger,
        "stage_start",
        stage=StageName.MONDAY_STATUS.value,
        task_id=metadata.task_id,
        payload_count=len(records),
    )

    if not records:
        structured_log(
            logger,
            "no_records",
            stage=StageName.MONDAY_STATUS.value,
            task_id=metadata.task_id,
        )
        stage_result.mark_finished(success=True)
        stage_result.data["processed"] = []
        return stage_result

    monday_page = MondayPage(driver)
    driver.get(metadata.base_urls.get(StageName.MONDAY.value, metadata.base_urls.get("monday", "")))

    try:
        structured_log(
            logger,
            "login_step",
            stage=StageName.MONDAY_STATUS.value,
            task_id=metadata.task_id,
        )
        if monday_page.is_login_page():
            cred = (
                metadata.credentials.get(StageName.MONDAY_STATUS.value)
                or metadata.credentials.get(StageName.MONDAY.value)
                or metadata.credentials.get("monday")
            )
            if not cred:
                raise RuntimeError("Monday credentials not supplied for status update")
            monday_page.login(cred.username, cred.password)
        monday_page.click_welcome_letter_qc()
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.MONDAY_STATUS, "board_loaded")
        )
    except Exception as exc:  # pragma: no cover
        structured_log(
            logger,
            "login_failure",
            stage=StageName.MONDAY_STATUS.value,
            task_id=metadata.task_id,
            error=str(exc),
        )
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.MONDAY_STATUS, "login_failure")
        )
        stage_result.mark_finished(success=False, error=str(exc))
        return stage_result

    processed: List[Dict] = []
    failures: List[Dict] = []
    first_iteration = True

    for record in records:
        npi = str(record.get("npi_number") or record.get("npi"))
        if not npi:
            failures.append({"reason": "missing_npi", "record": record})
            continue

        try:
            structured_log(
                logger,
                "record_start",
                stage=StageName.MONDAY_STATUS.value,
                task_id=metadata.task_id,
                npi=npi,
            )

            if first_iteration:
                monday_page.click_search_button()
                first_iteration = False

            monday_page.enter_npi_button(npi)
            time.sleep(2)
            monday_page.click_not_started()
            monday_page.click_done_button()
            time.sleep(2)
            monday_page.click_cross_button()
            time.sleep(1)

            processed.append({"npi_number": npi, "status": "done"})
            structured_log(
                logger,
                "record_complete",
                stage=StageName.MONDAY_STATUS.value,
                task_id=metadata.task_id,
                npi=npi,
            )
        except Exception as exc:  # pragma: no cover
            structured_log(
                logger,
                "record_failure",
                stage=StageName.MONDAY_STATUS.value,
                task_id=metadata.task_id,
                npi=npi,
                error=str(exc),
            )
            failures.append({"npi_number": npi, "error": str(exc)})

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.MONDAY_STATUS.value,
        "processed": processed,
        "failed": failures,
    }
    post_webhook(metadata, StageName.MONDAY_STATUS, payload)

    stage_result.data["processed"] = processed
    stage_result.data["failed"] = failures
    stage_result.mark_finished(success=not failures)
    return stage_result
