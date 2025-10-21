"""Headless runner implementation for the QuickCap submission stage."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

import constants
from pages.quickcap_page import QuickcapPage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook, fetch_stage_payload

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


def _map_company(network: str, health_plan: str) -> Optional[str]:
    return constants.COMPANY_MAP.get((network or "").strip().lower(), {}).get((health_plan or "").strip().lower())


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    stage_result = StageResult(stage=StageName.QUICKCAP)
    records: List[Dict] = list(metadata.request_payload.get("records", []))

    structured_log(
        logger,
        "stage_start",
        stage=StageName.QUICKCAP.value,
        task_id=metadata.task_id,
        payload_count=len(records),
    )

    if not records:
        stage_result.mark_finished(success=True)
        stage_result.data["processed"] = []
        return stage_result

    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)

    driver.get(base_url)
    quickcap_page = QuickcapPage(driver)

    try:
        quickcap_page.login(cred.username, cred.password)
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, "after_login")
        )
    except Exception as exc:  # pragma: no cover
        structured_log(
            logger,
            "login_failure",
            stage=StageName.QUICKCAP.value,
            task_id=metadata.task_id,
            error=str(exc),
        )
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, "login_failure")
        )
        stage_result.mark_finished(success=False, error=str(exc))
        return stage_result

    processed: List[Dict] = []
    failures: List[Dict] = []
    current_company: Optional[str] = None

    for record in records:
        npi = str(record.get("npi_number") or record.get("npi") or "").strip()
        if not npi:
            failures.append({"reason": "missing_npi", "record": record})
            continue

        network = (record.get("network") or "").strip().lower()
        health_plan = (record.get("health_plan") or "").strip().lower()
        company_name = record.get("company") or _map_company(network, health_plan)

        try:
            structured_log(
                logger,
                "record_start",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi,
                company=company_name,
            )

            if company_name and company_name != current_company:
                if not quickcap_page.choose_company(company_name):
                    raise RuntimeError(f"Unable to switch to company {company_name}")
                current_company = company_name

            quickcap_page.choose_credentialing_tab()
            quickcap_page.choose_practitioner_data()
            quickcap_page.enter_npi(npi)
            quickcap_page.click_search_button()

            stage_result.artifacts.append(
                artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, f"search_{npi}")
            )
            processed.append({"npi_number": npi, "company": company_name})
        except Exception as exc:  # pragma: no cover
            failures.append({"npi_number": npi, "error": str(exc)})
            stage_result.artifacts.append(
                artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, f"failure_{npi}")
            )
            structured_log(
                logger,
                "record_failure",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi,
                error=str(exc),
            )

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.QUICKCAP.value,
        "processed": processed,
        "failed": failures,
    }
    post_webhook(metadata, StageName.QUICKCAP, payload)

    stage_result.data["processed"] = processed
    stage_result.data["failed"] = failures
    stage_result.mark_finished(success=not failures)
    return stage_result
