"""
Headless runner implementation for the PR Site enrichment stage.
"""

from __future__ import annotations

import logging
import time
from typing import List
from urllib.parse import quote, urlparse, urlunparse

from selenium.webdriver.remote.webdriver import WebDriver

from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from pages.pr_site_page import PRSitePage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log

logger = logging.getLogger(__name__)


def _get_credential(metadata: RunnerMetadata) -> CredentialRef:
    candidates = [
        metadata.credentials.get(StageName.PR_SITE.value),
        metadata.credentials.get("pr_site"),
    ]
    for cred in candidates:
        if cred:
            return cred
    raise RuntimeError("PR Site credentials not supplied in RunnerMetadata")


def _get_base_url(metadata: RunnerMetadata) -> str:
    candidates = [
        metadata.base_urls.get(StageName.PR_SITE.value),
        metadata.base_urls.get("pr_site"),
        "https://pss.ad.pns-mgmt.com/ProvPractice.aspx#s1",
    ]
    for url in candidates:
        if url:
            return url
    raise RuntimeError("PR Site base URL not configured")


def _inject_basic_auth(url: str, cred: CredentialRef) -> str:
    parsed = urlparse(url)
    if not parsed.netloc:
        raise RuntimeError(f"Invalid PR Site URL: {url}")
    if "@" in parsed.netloc:
        return url  # already contains basic auth
    username = quote(cred.username, safe="")
    password = quote(cred.password, safe="")
    netloc = f"{username}:{password}@{parsed.netloc}"
    return urlunparse(parsed._replace(netloc=netloc))


def _collect_npi_records(db) -> List[PRSiteData]:
    return db.query(PRSiteData).filter(PRSiteData.status == 0).all()


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    """
    Execute the PR Site enrichment stage.

    Retrieves pending NPIs (status=0), fetches demographic data from the PR Site
    portal, and updates the `pr_site_data` table accordingly (status ➜ 1).
    """
    stage_result = StageResult(stage=StageName.PR_SITE)
    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)
    auth_url = _inject_basic_auth(base_url, cred)

    structured_log(logger, "stage_start", stage=StageName.PR_SITE.value, task_id=metadata.task_id, url=base_url)

    db = SessionLocal()
    processed: List[str] = []
    try:
        records = _collect_npi_records(db)
        structured_log(logger, "records_loaded", task_id=metadata.task_id, count=len(records))
        if not records:
            stage_result.artifacts.append(
                artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, "idle")
            )
            stage_result.mark_finished(success=True)
            stage_result.data["processed"] = []
            return stage_result

        driver.get(auth_url)
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, "login")
        )

        pr_site_page = PRSitePage(driver)

        for record in records:
            npi = str(record.npi_number)
            try:
                structured_log(logger, "record_start", task_id=metadata.task_id, npi=npi)

                pr_site_page.hover_over_practice_menu()
                pr_site_page.enter_npi_search(npi)
                pr_site_page.click_search_npi()
                time.sleep(5)
                group_npi = pr_site_page.get_group_npi()
                if group_npi:
                    pr_site_page.get_ind_npi_list_with_grp_npi_locations(record, group_npi)

                pr_site_page.hover_over_update_menuu()
                pr_site_page.enter_npi_search(npi)
                pr_site_page.click_search_npi()
                time.sleep(3)

                record.last_name = pr_site_page.get_last_name() or record.last_name
                record.first_name = pr_site_page.get_first_name() or record.first_name
                record.gender = pr_site_page.get_gender() or record.gender
                record.npi_number = int(pr_site_page.get_npi_number() or record.npi_number)
                record.city = pr_site_page.get_city() or record.city
                record.state = pr_site_page.get_state() or record.state
                record.zip_code = (pr_site_page.get_zip_code() or record.zip_code or "").replace("-", "")
                record.category = pr_site_page.get_category() or record.category
                record.speciality = pr_site_page.get_speciality() or record.speciality
                record.network = pr_site_page.get_network() or record.network
                taxonomy_code = pr_site_page.get_taxonomy_code()
                if taxonomy_code:
                    record.taxonomy_code = taxonomy_code
                record.status = 1

                db.commit()
                processed.append(npi)
                stage_result.artifacts.append(
                    artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, f"success_{npi}")
                )
                structured_log(logger, "record_success", task_id=metadata.task_id, npi=npi)
            except Exception as record_exc:
                db.rollback()
                structured_log(logger, "record_failure", task_id=metadata.task_id, npi=npi, error=str(record_exc))
                stage_result.artifacts.append(
                    artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, f"failure_{npi}")
                )
                stage_result.artifacts.append(
                    artifacts.capture_dom(driver, metadata, StageName.PR_SITE, f"failure_{npi}")
                )

        stage_result.data["processed"] = processed
        stage_success = all_npis_processed(processed, records)
        stage_result.mark_finished(success=stage_success)
        if not stage_success:
            structured_log(
                logger,
                "stage_partial",
                task_id=metadata.task_id,
                stage=StageName.PR_SITE.value,
                processed=len(processed),
                total=len(records),
            )
    except Exception as exc:  # pragma: no cover - live system dependency
        structured_log(
            logger,
            "stage_exception",
            task_id=metadata.task_id,
            stage=StageName.PR_SITE.value,
            error=str(exc),
        )
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, "stage_exception")
        )
        stage_result.artifacts.append(
            artifacts.capture_dom(driver, metadata, StageName.PR_SITE, "stage_exception")
        )
        stage_result.mark_finished(success=False, error=str(exc))
    finally:
        db.close()

    return stage_result


def all_npis_processed(processed: List[str], records: List[PRSiteData]) -> bool:
    if not records:
        return True
    return len(processed) == len(records)
