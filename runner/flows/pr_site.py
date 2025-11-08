"""Headless runner implementation for the PR Site enrichment stage."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
from urllib.parse import urlparse, urlunparse

from selenium.webdriver.remote.webdriver import WebDriver

from pages.pr_site_page import PRSitePage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import (
    post_webhook,
    post_update_state_task_units,
    post_micro_update_task_units,
)
from ..auth import request_with_auth
from requests import RequestException
from monitoring import events
from taskunits.wla_npi import NpiWlaTU

TASK_UNITS_BASE_URL = "http://0.0.0.0:10022/api/task_units"

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


def _load_task_unit_dict(task_id: str) -> Dict[str, Dict[str, Any]]:
    if not task_id:
        return {}
    url = f"{TASK_UNITS_BASE_URL}/{task_id}"
    try:
        response = request_with_auth("GET", url, timeout=30)
        response.raise_for_status()
        task_units = response.json()
    except RequestException as exc:
        logger.warning(
            "Failed to fetch task units",
            extra={"task_id": task_id, "url": url, "error": str(exc)},
        )
        return {}
    mapping: Dict[str, Dict[str, Any]] = {}
    for unit in task_units or []:
        identifier = str(unit.get("identifier") or "").strip()
        if not identifier:
            continue
        mapping[identifier] = unit
        normalized = identifier.lstrip("0")
        if normalized and normalized not in mapping:
            mapping[normalized] = unit
    return mapping


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    stage_result = StageResult(stage=StageName.PR_SITE)
    task_unit_dict: Dict[str, Dict[str, Any]] = _load_task_unit_dict(metadata.task_id)

    structured_log(
        logger,
        "stage_start",
        stage=StageName.PR_SITE.value,
        task_id=metadata.task_id,
        payload_count=len(task_unit_dict),
    )

    if not task_unit_dict:
        stage_result.mark_finished(success=True)
        return stage_result

    def _task_unit_for_npi(npi_value: str) -> Optional[Dict[str, Any]]:
        normalized = str(npi_value or "").strip()
        if not normalized:
            return None
        if normalized in task_unit_dict:
            return task_unit_dict[normalized]
        alt_identifier = normalized.lstrip("0")
        if alt_identifier and alt_identifier in task_unit_dict:
            return task_unit_dict[alt_identifier]
        return None

    def _record_state_transition(
        npi_value: str,
        new_state: int,
        message: str,
        data_payload: Optional[Dict[str, Any]] = None,
        micro_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        task_unit = _task_unit_for_npi(npi_value)
        if not task_unit:
            logger.debug("Task unit not found for NPI %s; skipping state update", npi_value)
            return
        update_meta = {"npi": npi_value}
        if data_payload:
            update_meta.update(data_payload)
        state_update_payload = {
            "updates": [
                {
                    "task_unit_id": task_unit["task_unit_id"],
                    "state": str(new_state),
                    "transition_reason": message,
                    "state_value": 0,
                    "meta_data": update_meta,
                }
            ]
        }
        post_update_state_task_units(payload=state_update_payload)
        task_unit["current_state"] = new_state
        update_data = {"message": message, "npi": npi_value}
        if micro_extra:
            update_data.update(micro_extra)
        elif data_payload:
            update_data.update(data_payload)
        post_micro_update_task_units(
            payload={
                "updates": [
                    {
                        "task_unit_id": task_unit["task_unit_id"],
                        "update_state": new_state,
                        "update_data": update_data,
                    }
                ]
            }
        )

    def _record_micro_update(
        npi_value: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        state_override: Optional[int] = None,
    ) -> None:
        task_unit = _task_unit_for_npi(npi_value)
        if not task_unit:
            logger.debug("Task unit not found for NPI %s; skipping micro update", npi_value)
            return
        update_data = {"message": message, "npi": npi_value}
        if extra:
            update_data.update(extra)
        payload = {
            "updates": [
                {
                    "task_unit_id": task_unit["task_unit_id"],
                    "update_state": state_override if state_override is not None else task_unit.get("current_state"),
                    "update_data": update_data,
                }
            ]
        }
        post_micro_update_task_units(payload=payload)

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

    processed_task_unit_ids = set()
    for identifier, task_unit in task_unit_dict.items():
        task_unit_id = task_unit.get("task_unit_id")
        if not task_unit_id or task_unit_id in processed_task_unit_ids:
            continue
        processed_task_unit_ids.add(task_unit_id)

        npi = str(identifier or task_unit.get("identifier") or "").strip()
        if not npi:
            failures.append(
                {
                    "reason": "missing_task_unit_identifier",
                    "task_unit_id": task_unit_id,
                    "task_unit": task_unit,
                }
            )
            _record_micro_update(
                "unknown",
                "Task unit missing identifier; skipping PR Site enrichment",
                extra={"task_unit_id": task_unit_id},
            )
            continue

        record = dict(task_unit)
        record.setdefault("npi_number", npi)
        attempt = int(record.get("attempt", 1) or 1)

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
                "identifier": npi,
                "task_unit_id": task_unit_id,
                "npi_number": npi,
                "last_name": pr_site_page.get_last_name().upper(),
                "first_name": pr_site_page.get_first_name().upper(),
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
            _record_state_transition(
                npi,
                NpiWlaTU.TU_PROVIDER_PERSONAL_DETAILS_FETCHED,
                "Fetched provider personal details from PR Site",
                data_payload=data,
            )
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
                _record_state_transition(
                    npi,
                    NpiWlaTU.TU_GROUP_DETAILS_FETCHED,
                    "Fetched group details from PR Site",
                    data_payload=data,
                )
                addresses = pr_site_page.get_ind_npi_list_with_grp_npi_locations(record, group_npi)
                if addresses:
                    data["practice_addresses"] = addresses
                    _record_state_transition(
                        npi,
                        NpiWlaTU.TU_GROUP_ADDRESS_FETCHED,
                        "Fetched group practice addresses from PR Site",
                        data_payload=data,
                    )
                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.PR_SITE,
                        npi=npi,
                        status="completed",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
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
                    _record_micro_update(
                        npi,
                        "No practice addresses found for this NPI on PR Site",
                    )
                #     payload = {
                #         "task_id": metadata.task_id,
                #         "stage": StageName.PR_SITE.value,
                #         "records": enriched,
                #         "failed": failures,
                #     }
                #     post_webhook(metadata, StageName.PR_SITE, payload)
            except Exception as inner_exc:  # pragma: no cover
                structured_log(
                    logger,
                    "practice_lookup_failure",
                    stage=StageName.PR_SITE.value,
                    task_id=metadata.task_id,
                    npi=npi,
                    error=str(inner_exc),
                )
                _record_micro_update(
                    npi,
                    "Failed to fetch group or practice details from PR Site",
                    extra={"error": str(inner_exc)},
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
            _record_state_transition(
                npi,
                NpiWlaTU.TU_ERROR_ORG_ID_NOT_FOUND,
                "Failed to enrich PR Site data",
                data_payload={"error": str(exc)},
                micro_extra={"error": str(exc)},
            )
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
