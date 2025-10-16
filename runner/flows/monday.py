"""
Headless runner implementation for the Monday.com ingestion stage.
"""

from __future__ import annotations

import logging
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from pages.monday_page import MondayPage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log

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


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    """
    Execute the Monday.com ingestion stage.

    Steps:
        1. Navigate to Monday board and authenticate.
        2. Collect NPIs in \"Not Started\" state.
        3. Insert fresh rows into `pr_site_data` with status=0.
        4. Capture artifacts (screenshot + JSON dump).
    """
    stage_result = StageResult(stage=StageName.MONDAY)
    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)

    structured_log(logger, "stage_start", stage=StageName.MONDAY.value, task_id=metadata.task_id, url=base_url)

    monday_page = MondayPage(driver)
    driver.get(base_url)

    try:
        monday_page.login(cred.username, cred.password)
        artifacts.capture_screenshot(driver, metadata, StageName.MONDAY, "after_login")

        monday_page.click_welcome_letter_qc()
        npis = monday_page.get_pr_site_npis()
        structured_log(logger, "npis_collected", task_id=metadata.task_id, count=len(npis))

        artifact = artifacts.capture_json(npis, metadata, StageName.MONDAY, "npis")
        stage_result.artifacts.append(artifact)

        db = SessionLocal()
        try:
            for entry in npis:
                record = PRSiteData(
                    npi_number=entry.get("npi_number"),
                    effective_date=entry.get("effective_date"),
                    health_plan=entry.get("health_plan"),
                    lines_of_business=entry.get("lines_of_business"),
                    status=0,
                )
                db.add(record)
            db.commit()
            structured_log(logger, "db_commit", task_id=metadata.task_id, inserted=len(npis))
        finally:
            db.close()

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
        artifacts.capture_screenshot(driver, metadata, StageName.MONDAY, "failure")
        artifacts.capture_dom(driver, metadata, StageName.MONDAY, "failure")
        stage_result.mark_finished(success=False, error=str(exc))
        return stage_result

    return stage_result
