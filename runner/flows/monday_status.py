"""Headless runner implementation for updating Monday board statuses."""

from __future__ import annotations

import datetime as _dt
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
from selenium.webdriver.remote.webdriver import WebDriver
from ..auth import request_with_auth
from pages.monday_status_page import MondayStatusPage
from .. import artifacts
from ..context import RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook, fetch_stage_payload
from monitoring import events
from taskunits.wla_npi import NpiWlaTU
logger = logging.getLogger(__name__)

TASK_UNITS_BASE_URL = "http://0.0.0.0:10022/api/task_units"

def safe_str(value: Any) -> str:
    """Safely convert value to string, handling None."""
    return str(value) if value is not None else ""

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
    stage_result = StageResult(stage=StageName.MONDAY_STATUS)
    """
    TODO Yash: create task unit
    - In the beginning of any task or stage, we will initialise the relevant task unit dictionary.
    """
    stage_run_id = uuid4().hex
    stage_started_at = _dt.datetime.now(_dt.timezone.utc)
    stage_artifact_refs: List[Dict[str, Any]] = []
    task_unit_dict: Dict[str, Dict[str, Any]] = _load_task_unit_dict(metadata.task_id)
    if not task_unit_dict:
        stage_result.mark_finished(success=True)
        return stage_result

    def _task_unit_for_npi(npi_value: str) -> Optional[Dict[str, Any]]:
        normalized = str(npi_value or "").strip()
        if not normalized:
            return None

        # Exact match first
        if normalized in task_unit_dict:
            return task_unit_dict[normalized]

        # Remove leading zeros (01932120326 -> 1932120326)
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
                    "update_type": extra.get("update_type",0),
                    "message": message
                }
            ]
        }
        post_micro_update_task_units(payload=payload)

    task_unit_dict = _load_task_unit_dict(metadata.task_id)
    records: List[Dict[str, Any]] = list(task_unit_dict.values())


    if not records:
        stage_result.mark_finished(success=True)
        stage_result.data["processed"] = []
        stage_result.data["failed"] = []
        finished_at = _dt.datetime.now(_dt.timezone.utc)
        events.emit_stage_event(
            task_id=metadata.task_id,
            stage=StageName.QUICKCAP,
            event="stage_completed",
            status="completed",
            stage_run_id=stage_run_id,
            started_at=stage_started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
            summary={"records_total": 0, "records_success": 0, "records_failed": 0},
            artifacts=stage_artifact_refs,
        )
        return stage_result

    monday_page = MondayStatusPage(driver)
    base_url = (
        metadata.base_urls.get(StageName.MONDAY_STATUS.value)
        or metadata.base_urls.get(StageName.MONDAY)
        or metadata.base_urls.get("monday")
    )
    if not base_url:
        raise RuntimeError("Monday base URL not configured for status update")
    driver.get(base_url)

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
                "Task unit missing identifier; skipping monday status update enrichment",
                extra={"task_unit_id": task_unit_id,
                       "update_type": 3
                       }
            )
            continue

        record = dict(task_unit)
        record.setdefault("npi_number", npi)
        attempt = int(record.get("attempt", 1) or 1)
        artifact_start = len(stage_result.artifacts)

    try:
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
        board_artifact = artifacts.capture_screenshot(driver, metadata, StageName.MONDAY_STATUS, "board_loaded")
        stage_result.artifacts.append(board_artifact)
        board_refs = events.upload_artifacts(
            task_id=metadata.task_id,
            stage=StageName.MONDAY_STATUS,
            artifacts=[board_artifact],
        )
        stage_artifact_refs.extend(dict(ref) for ref in board_refs)
    except Exception as exc:  # pragma: no cover
        structured_log(
            logger,
            "login_failure",
            stage=StageName.MONDAY_STATUS.value,
            task_id=metadata.task_id,
            error=str(exc),
        )
        failure_artifact = artifacts.capture_screenshot(driver, metadata, StageName.MONDAY_STATUS, "login_failure")
        stage_result.artifacts.append(failure_artifact)
        failure_refs = events.upload_artifacts(
            task_id=metadata.task_id,
            stage=StageName.MONDAY_STATUS,
            artifacts=[failure_artifact],
        )
        stage_artifact_refs.extend(dict(ref) for ref in failure_refs)
        stage_result.mark_finished(success=False, error=str(exc))
        finished_at = _dt.datetime.now(_dt.timezone.utc)
        events.emit_stage_event(
            task_id=metadata.task_id,
            stage=StageName.MONDAY_STATUS,
            event="stage_failed",
            status="failed",
            stage_run_id=stage_run_id,
            started_at=stage_started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
            message=str(exc),
            artifacts=stage_artifact_refs,
        )
        return stage_result

    processed: List[Dict] = []
    failures: List[Dict] = []
    first_iteration = True

    for record in records:
        # current_state = int(record.get("current_state") or "")
        npi = str(record.get("npi_number") or record.get("npi"))
        task_unit = _task_unit_for_npi(npi)
        if task_unit:
            record_status = safe_str(task_unit.get("current_state"))
        else:
            # fallback if something is broken
            record_status = safe_str(record.get("current_state"))
        health_plan = safe_str(record.get("health_plan"))
        effective_date = safe_str(record.get("effective_date"))
        lines_of_business = safe_str(record.get("lines_of_business"))
        address = safe_str(record.get("address_line1"))
        remarks = safe_str(record.get("remarks"))
        attempt = int(record.get("attempt", 1) or 1)
        result_status = "completed"
        result_message: Optional[str] = None
        output_snapshot: Dict[str, Any] = {"npi_number": npi or "unknown", "status": "pending"}

        if not npi:
            # failure_entry = {"reason": "missing_npi", "record": record}
            # failures.append(failure_entry)
            # result_status = "failed"
            # result_message = "missing_npi"
            failures.append({"reason": "missing_npi", "record": record})
            _record_micro_update(
                record,
                "unknown",
                "Task unit missing NPI; skipping Monday Status Processing",
                extra={"record": record},
            )
            continue

        try:
            if record_status in {"5", "7"}:
                if first_iteration:
                    monday_page.click_search_button()
                    first_iteration = False

                monday_page.enter_npi_button(npi)
                # time.sleep(2)

                monday_health_plans = monday_page.get_all_health_plans_from_ui()

                health_plan_match = False
                db_health_plan_clean = health_plan.strip().lower() if health_plan else ""

                if monday_health_plans and db_health_plan_clean:
                    for monday_health_plan in monday_health_plans:
                        monday_health_plan_clean = monday_health_plan.strip().lower()
                        # Handle truncated names and partial matches
                        if (monday_health_plan_clean == db_health_plan_clean or
                                db_health_plan_clean.startswith(
                                    monday_health_plan_clean.replace('...', '').replace('…', '').strip()) or
                                monday_health_plan_clean.startswith(db_health_plan_clean.split()[0].lower())):
                            health_plan_match = True
                            break

                if health_plan_match:
                    if record_status == "5":
                        monday_page.click_not_started_for_matching_health_plans(
                            db_health_plan=health_plan)
                        monday_page.click_review_button()
                        # time.sleep(2)
                        monday_page.click_cross_button()
                        enriched: List[Dict] = [
                            {
                                "npi": npi,
                                "health_plan": health_plan,
                                "effective_date": effective_date,
                                "lines_of_business": lines_of_business,
                                "update_status": 3,
                            }
                        ]
                        data1 = {
                            "task_id": metadata.task_id,
                            "stage": StageName.MONDAY_STATUS.value,
                            "failed": failures,
                            "records": enriched
                        }
                        post_webhook(metadata, StageName.MONDAY_STATUS, data1)
                        """
                        TODO Yash: update unit
                        marks as review
                        """
                        # record.status = 3
                        # db.commit()

                        structured_log(
                            logger,
                            "record_marked_done",
                            stage=StageName.MONDAY_STATUS.value,
                            task_id=metadata.task_id,
                            npi=npi,
                            health_plan=health_plan,
                        )
                        output_snapshot = {"npi_number": npi, "status": "done"}

                    elif record_status == "7":

                        if remarks:
                            remarks_text = remarks
                            structured_log(
                                logger,
                                "remarks_found",
                                stage=StageName.MONDAY_STATUS.value,
                                task_id=metadata.task_id,
                                npi=npi,
                            )
                        else:
                            remarks_text = "Organisation Data Missing"
                            structured_log(
                                logger,
                                "remarks_defaulted",
                                stage=StageName.MONDAY_STATUS.value,
                                task_id=metadata.task_id,
                                npi=npi,
                            )

                        remarks_added = monday_page.process_rows_and_enter_remarks(
                            db_health_plan=health_plan,
                            db_effective_date=effective_date,
                            remarks_text=remarks_text
                        )

                        if remarks_added:
                            structured_log(
                                logger,
                                "remarks_added",
                                stage=StageName.MONDAY_STATUS.value,
                                task_id=metadata.task_id,
                                npi=npi,
                            )
                            # Continue with Roadblock process
                            # monday_status_test.click_not_started()
                            monday_page.click_not_started_for_matching_health_plans(
                                db_health_plan=health_plan)
                            monday_page.click_roadblock_button()
                            # time.sleep(2)
                            monday_page.click_cross_button()
                            enriched: List[Dict] = [
                                {
                                    "npi": npi,
                                    "health_plan": health_plan,
                                    "effective_date": effective_date,
                                    "lines_of_business": lines_of_business,
                                    "update_status": 6,
                                }
                            ]
                            data1 = {
                                "task_id": metadata.task_id,
                                "stage": StageName.MONDAY_STATUS.value,
                                "failed": failures,
                                "records": enriched
                            }
                            post_webhook(metadata, StageName.MONDAY_STATUS, data1)
                            """
                            TODO Yash: update unit
                            marks as review
                            """
                            # record.status = 6
                            # db.commit()
                            output_snapshot = {"npi_number": npi, "status": "roadblock"}
                            processed.append({"npi_number": npi, "status": "roadblock"})
                        else:
                            _record_micro_update(
                                record,
                                npi,
                                "Reamrks not added",
                                extra={"error": message or "unknown", "update_type": 3},
                            )
                            structured_log(
                                logger,
                                "remarks_not_added",
                                stage=StageName.MONDAY_STATUS.value,
                                task_id=metadata.task_id,
                                npi=npi,
                                reason="no_matching_rows",
                            )
                            result_message = "remarks_not_added"
                            output_snapshot = {
                                "npi_number": npi,
                                "status": "remarks_not_added",
                                "reason": "no_matching_rows",
                            }
                    else:
                        structured_log(
                            logger,
                            "remarks_missing",
                            stage=StageName.MONDAY_STATUS.value,
                            task_id=metadata.task_id,
                            npi=npi,
                        )
                        result_message = "remarks_missing"
                        output_snapshot = {"npi_number": npi, "status": "remarks_missing"}
                else:
                    if monday_health_plans:
                        monday_plans_str = ", ".join(monday_health_plans)

                    else:
                        monday_plans_str = "No health plans found in UI"
                    structured_log(
                        logger,
                        "health_plan_mismatch",
                        stage=StageName.MONDAY_STATUS.value,
                        task_id=metadata.task_id,
                        npi=npi,
                        db_health_plan=health_plan,
                        monday_health_plans=monday_plans_str,
                    )
                    _record_micro_update(
                        record,
                        npi,
                        "Health plan doesn't match",
                        extra={"error": message or "unknown", "update_type": 3},
                    )
                    processed.append({"npi_number": npi, "status": "done"})
                    result_message = "health_plan_mismatch"
                    output_snapshot = {
                        "npi_number": npi,
                        "status": "health_plan_mismatch",
                        "monday_health_plans": monday_plans_str,
                    }
                    continue
            else:
                output_snapshot = {"npi_number": npi, "status": "no_action"}
                structured_log(
                    logger,
                    "record_no_action",
                    stage=StageName.MONDAY_STATUS.value,
                    task_id=metadata.task_id,
                    npi=npi,
                    record_status=record_status,
                )
                result_message = "no_action"

            # if first_iteration:
            #     monday_page.click_search_button()
            #     first_iteration = False
            #
            # monday_page.enter_npi_button(npi)
            # time.sleep(2)
            # monday_page.click_not_started()
            # monday_page.click_done_button()
            # time.sleep(2)
            # monday_page.click_cross_button()
            # time.sleep(1)

            # processed.append({"npi_number": npi, "status": "done"})


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
            result_status = "failed"
            result_message = str(exc)
            output_snapshot = {"npi_number": npi, "error": result_message}
        finally:
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.MONDAY_STATUS,
                npi=npi or "unknown",
                status="completed" if result_status == "completed" else "failed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=output_snapshot,
                message=result_message,
            )
            _record_state_transition(
                record,
                npi,
                NpiWlaTU.TU_UPDATE_STATUS_ON_MONDAY,
                "Monday Status updated",
                micro_extra={"update_type": 1}
            )

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.MONDAY_STATUS.value,
        "processed": processed,
        "failed": failures,
    }
    post_webhook(metadata, StageName.MONDAY_STATUS, payload)
    """
    TODO Yash: update unit
    stage: complete
    """
    stage_result.data["processed"] = processed
    stage_result.data["failed"] = failures
    success = not failures
    stage_result.mark_finished(success=success)
    finished_at = _dt.datetime.now(_dt.timezone.utc)
    events.emit_stage_event(
        task_id=metadata.task_id,
        stage=StageName.MONDAY_STATUS,
        event="stage_completed" if success else "stage_failed",
        status="completed" if success else "failed",
        stage_run_id=stage_run_id,
        started_at=stage_started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
        summary={
            "records_total": len(records),
            "records_success": len(processed),
            "records_failed": len(failures),
        },
        message=None if success else "one_or_more_records_failed",
        artifacts=stage_artifact_refs,
    )
    structured_log(
        logger,
        "stage_finished",
        stage=StageName.MONDAY_STATUS.value,
        task_id=metadata.task_id,
        stage_run_id=stage_run_id,
        success=success,
        failures=len(failures),
    )
    return stage_result
