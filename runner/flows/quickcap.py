"""
Headless runner implementation for the QuickCap submission stage.

NOTE: This initial port focuses on establishing the headless plumbing,
logging, and database state transitions. The UI interactions needed to
complete Quick Add workflows should be implemented in a follow-up pass.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

import constants
from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from pages.quickcap_page import QuickcapPage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log

logger = logging.getLogger(__name__)


def _get_credential(metadata: RunnerMetadata) -> CredentialRef:
    candidates = [
        metadata.credentials.get(StageName.QUICKCAP.value),
        metadata.credentials.get("quickcap"),
    ]
    for cred in candidates:
        if cred:
            return cred
    raise RuntimeError("QuickCap credentials not supplied in RunnerMetadata")


def _get_base_url(metadata: RunnerMetadata) -> str:
    candidates = [
        metadata.base_urls.get(StageName.QUICKCAP.value),
        metadata.base_urls.get("quickcap"),
        "https://pnstest.quickcap.net",
    ]
    for url in candidates:
        if url:
            return url
    raise RuntimeError("QuickCap base URL not configured")


def _collect_records(db) -> List[PRSiteData]:
    return db.query(PRSiteData).filter(PRSiteData.status == 1).all()


def _map_company(record: PRSiteData) -> Optional[str]:
    network = (record.network or "").strip().lower()
    health_plan = (record.health_plan or "").strip().lower()
    return constants.COMPANY_MAP.get(network, {}).get(health_plan)


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    """
    Execute the QuickCap submission stage.

    Currently, the implementation validates credentials, captures artifacts,
    and marks eligible records as processed (status=2).  UI automation for
    QuickCap data entry will be added in a future iteration.
    """
    stage_result = StageResult(stage=StageName.QUICKCAP)
    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)

    structured_log(logger, "stage_start", stage=StageName.QUICKCAP.value, task_id=metadata.task_id, url=base_url)

    driver.get(base_url)
    quickcap_page = QuickcapPage(driver)

    try:
        quickcap_page.click_company()
        quickcap_page.login(cred.username, cred.password)
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, "after_login")
        )
    except Exception as exc:
        structured_log(
            logger,
            "login_failure",
            task_id=metadata.task_id,
            stage=StageName.QUICKCAP.value,
            error=str(exc),
        )
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, "login_failure")
        )
        stage_result.artifacts.append(
            artifacts.capture_dom(driver, metadata, StageName.QUICKCAP, "login_failure")
        )
        stage_result.mark_finished(success=False, error=str(exc))
        return stage_result

    db = SessionLocal()
    processed: List[int] = []
    skipped: Dict[str, str] = {}
    try:
        records = _collect_records(db)
        structured_log(logger, "records_loaded", task_id=metadata.task_id, count=len(records))
        if not records:
            stage_result.mark_finished(success=True)
            stage_result.data["processed"] = []
            return stage_result

        for record in records:
            company = _map_company(record)
            if not company:
                skipped[str(record.npi_number)] = "company_mapping_missing"
                structured_log(
                    logger,
                    "record_skipped",
                    task_id=metadata.task_id,
                    npi=record.npi_number,
                    reason="company_mapping_missing",
                )
                continue

            # Placeholder for future UI automation.
            record.status = 2
            record.updated_at = datetime.utcnow()
            processed.append(record.npi_number)

        db.commit()
        structured_log(logger, "records_updated", task_id=metadata.task_id, count=len(processed))
    except Exception as exc:  # pragma: no cover - depends on live systems
        db.rollback()
        structured_log(
            logger,
            "stage_exception",
            task_id=metadata.task_id,
            stage=StageName.QUICKCAP.value,
            error=str(exc),
        )
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, "exception")
        )
        stage_result.artifacts.append(
            artifacts.capture_dom(driver, metadata, StageName.QUICKCAP, "exception")
        )
        stage_result.mark_finished(success=False, error=str(exc))
        return stage_result
    finally:
        db.close()

    stage_result.data["processed"] = processed
    stage_result.data["skipped"] = skipped
    stage_result.mark_finished(success=len(processed) > 0 or not skipped)
    return stage_result

