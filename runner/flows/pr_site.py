"""Headless runner implementation for the PR Site enrichment stage."""

from __future__ import annotations

import logging
import time
from typing import Dict, List
from uuid import uuid4
from urllib.parse import urlparse, urlunparse

from selenium.webdriver.remote.webdriver import WebDriver

from pages.pr_site_page import PRSitePage
import re
from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook, fetch_stage_payload
from monitoring import events

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
    if parsed.username or parsed.password:
        return url
    netloc = f"{cred.username}:{cred.password}@{parsed.netloc}"
    return urlunparse(parsed._replace(netloc=netloc))


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    stage_result = StageResult(stage=StageName.PR_SITE)
    records: List[Dict] = list(metadata.request_payload.get("records", []))
    if not records:
        payload = fetch_stage_payload(metadata, StageName.PR_SITE)
        if payload:
            records = list(payload.get("records", []))

    structured_log(
        logger,
        "stage_start",
        stage=StageName.PR_SITE.value,
        task_id=metadata.task_id,
        payload_count=len(records),
    )

    if not records:
        stage_result.mark_finished(success=True)
        stage_result.data["records"] = []
        return stage_result

    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)
    auth_url = _inject_basic_auth(base_url, cred)

    driver.get(auth_url)
    stage_result.artifacts.append(
        artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, "login")
    )

    pr_site_page = PRSitePage(driver)
    stage_run_id = uuid4().hex
    enriched: List[Dict] = []
    failures: List[Dict] = []

    for record in records:
        raw_npi = record.get("npi_number") or record.get("npi")
        npi = str(raw_npi or "").strip()
        attempt = int(record.get("attempt", 1) or 1)
        if not npi:
            failures.append({"reason": "missing_npi", "record": record})
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.PR_SITE,
                npi="unknown",
                status="failed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                message="missing_npi",
            )
            continue

        events.emit_npi_event(
            task_id=metadata.task_id,
            stage=StageName.PR_SITE,
            npi=npi,
            status="in_progress",
            attempt=attempt,
            stage_run_id=stage_run_id,
            input_snapshot=record,
        )
        artifact_start = len(stage_result.artifacts)

        try:
            structured_log(
                logger,
                "record_start",
                stage=StageName.PR_SITE.value,
                task_id=metadata.task_id,
                npi=npi,
            )

            pr_site_page.hover_over_update_menuu()
            pr_site_page.enter_npi_search(npi)
            pr_site_page.click_search_npi()
            time.sleep(3)

            data = {
                "npi_number": npi,
                "last_name": pr_site_page.get_last_name(),
                "first_name": pr_site_page.get_first_name(),
                "gender": pr_site_page.get_gender(),
                "city": pr_site_page.get_city(),
                "state": pr_site_page.get_state(),
                "zip_code": pr_site_page.get_zip_code(),
                "category": pr_site_page.get_category(),
                "speciality": pr_site_page.get_speciality(),
                "network": pr_site_page.get_network(),
                "taxonomy_code": pr_site_page.get_taxonomy_code(),
                "effective_date": record.get("effective_date"),
                "health_plan": record.get("health_plan"),
                "lines_of_business": record.get("lines_of_business"),
            }
            input_snapshot1 = {
                "first_name": data["first_name"],
                "last_name": data["last_name"],
            }
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.PR_SITE,
                npi=npi,
                status="completed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=input_snapshot1,
                output_snapshot=data,
            )
            try:

                pr_site_page.hover_over_practice_menu()
                pr_site_page.enter_npi_search(npi)
                pr_site_page.click_search_npi()
                time.sleep(3)
                group_npi = pr_site_page.get_group_npi()
                group_name = pr_site_page.get_group_name()
                data["group_npi"] = group_npi
                data["group_name"] = group_name
                addresses = pr_site_page.get_ind_npi_list_with_grp_npi_locations(record, group_npi)

                pr_site_page.hover_over_group_menu()
                group_npi_num = pr_site_page.extract_number_from_string(group_npi)
                match = re.search(r'\d+', group_npi)
                group_npi_num1 = match.group() if match else group_npi
                pr_site_page.enter_group_npi_search(group_npi_num)
                pr_site_page.click_search_group_npi()
                group_tin = pr_site_page.get_group_tin()
                data["group_tin"] = group_tin
                if addresses:
                    data["practice_addresses"] = addresses
                    input_snapshot2 = [
                        {
                            "address_line_1": address_line_1,
                            "address_line_2": address_line_2,
                        }
                    ]
                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.PR_SITE,
                        npi=npi,
                        status="completed",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
                        input_snapshot=input_snapshot2,
                        output_snapshot=data,
                    )

                else:
                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.PR_SITE,
                        npi=npi,
                        status="completed",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
                        input_snapshot={"npi": npi},
                        output_snapshot=data,
                        message="No Addresses Found for this NPI",
                    )
                #     payload = {
                #         "task_id": metadata.task_id,
                #         "stage": StageName.PR_SITE.value,
                #         "records": enriched,
                #         "failed": failures,
                #     }
                #     post_webhook(metadata, StageName.PR_SITE, payload)
            except Exception as inner_exc:
                print(inner_exc)# pragma: no cover
                structured_log(
                    logger,
                    "practice_lookup_failure",
                    stage=StageName.PR_SITE.value,
                    task_id=metadata.task_id,
                    npi=npi,
                    error=str(inner_exc),
                )

            stage_result.artifacts.append(
                artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, f"success_{npi}")
            )
            enriched.append(data)
            structured_log(
                logger,
                "record_complete",
                stage=StageName.PR_SITE.value,
                task_id=metadata.task_id,
                npi=npi,
            )
            npi_artifacts = stage_result.artifacts[artifact_start:]
            artifact_refs = events.upload_artifacts(
                task_id=metadata.task_id,
                stage=StageName.PR_SITE,
                artifacts=npi_artifacts,
            )
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.PR_SITE,
                npi=npi,
                status="completed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=data,
                artifacts=artifact_refs,
            )
        except Exception as exc:  # pragma: no cover
            failures.append({"npi_number": npi, "error": str(exc)})
            stage_result.artifacts.append(
                artifacts.capture_screenshot(driver, metadata, StageName.PR_SITE, f"failure_{npi}")
            )
            stage_result.artifacts.append(
                artifacts.capture_dom(driver, metadata, StageName.PR_SITE, f"failure_{npi}")
            )
            structured_log(
                logger,
                "record_failure",
                stage=StageName.PR_SITE.value,
                task_id=metadata.task_id,
                npi=npi,
                error=str(exc),
            )
            npi_artifacts = stage_result.artifacts[artifact_start:]
            artifact_refs = events.upload_artifacts(
                task_id=metadata.task_id,
                stage=StageName.PR_SITE,
                artifacts=npi_artifacts,
            )
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.PR_SITE,
                npi=npi,
                status="failed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot={"error": str(exc)},
                artifacts=artifact_refs,
                message=str(exc),
            )

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.PR_SITE.value,
        "records": enriched,
        "failed": failures,
    }
    post_webhook(metadata, StageName.PR_SITE, payload)

    stage_result.data["records"] = enriched
    stage_result.data["failed"] = failures
    stage_result.mark_finished(success=not failures)
    return stage_result
