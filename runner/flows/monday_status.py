"""Headless runner implementation for updating Monday board statuses."""

from __future__ import annotations

import datetime as _dt
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from selenium.webdriver.remote.webdriver import WebDriver

from pages.monday_status_page import MondayStatusPage
from .. import artifacts
from ..context import RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook, fetch_stage_payload
from monitoring import events

logger = logging.getLogger(__name__)

def safe_str(value: Any) -> str:
    """Safely convert value to string, handling None."""
    return str(value) if value is not None else ""

def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    stage_result = StageResult(stage=StageName.MONDAY_STATUS)
    stage_run_id = uuid4().hex
    stage_started_at = _dt.datetime.now(_dt.timezone.utc)
    stage_artifact_refs: List[Dict[str, Any]] = []
    records: List[Dict] = list(metadata.request_payload.get("records", []))
    if not records:
        payload = fetch_stage_payload(metadata, StageName.MONDAY_STATUS)
        if payload:
            records = list(payload.get("records", [])) or list(payload.get("processed", []))

    structured_log(
        logger,
        "stage_start",
        stage=StageName.MONDAY_STATUS.value,
        task_id=metadata.task_id,
        payload_count=len(records),
    )
    events.emit_stage_event(
        task_id=metadata.task_id,
        stage=StageName.MONDAY_STATUS,
        event="stage_started",
        status="in_progress",
        stage_run_id=stage_run_id,
        started_at=stage_started_at.isoformat(),
        summary={"records_total": len(records)},
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
        stage_result.data["failed"] = []
        finished_at = _dt.datetime.now(_dt.timezone.utc)
        events.emit_stage_event(
            task_id=metadata.task_id,
            stage=StageName.MONDAY_STATUS,
            event="stage_completed",
            status="completed",
            stage_run_id=stage_run_id,
            started_at=stage_started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
            summary={"records_total": 0, "records_success": 0, "records_failed": 0},
            artifacts=stage_artifact_refs,
        )
        structured_log(
            logger,
            "stage_finished",
            stage=StageName.MONDAY_STATUS.value,
            task_id=metadata.task_id,
            stage_run_id=stage_run_id,
            success=True,
            failures=0,
        )
        return stage_result

    monday_page = MondayStatusPage(driver)
    base_url = (
        metadata.base_urls.get(StageName.MONDAY_STATUS.value)
        or metadata.base_urls.get(StageName.MONDAY.value)
        or metadata.base_urls.get("monday")
    )
    if not base_url:
        raise RuntimeError("Monday base URL not configured for status update")
    driver.get(base_url)

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
        structured_log(
            logger,
            "stage_finished",
            stage=StageName.MONDAY_STATUS.value,
            task_id=metadata.task_id,
            stage_run_id=stage_run_id,
            success=False,
            failures=len(records),
        )
        return stage_result

    processed: List[Dict] = []
    failures: List[Dict] = []
    first_iteration = True

    for record in records:
        npi = str(record.get("npi_number") or record.get("npi"))
        record_status = safe_str(record.get("status"))
        health_plan = safe_str(record.get("health_plan"))
        effective_date = safe_str(record.get("effective_date"))
        lines_of_business = safe_str(record.get("lines_of_business"))
        remarks = safe_str(record.get("remarks"))
        attempt = int(record.get("attempt", 1) or 1)
        result_status = "completed"
        result_message: Optional[str] = None
        output_snapshot: Dict[str, Any] = {"npi_number": npi or "unknown", "status": "pending"}

        if not npi:
            failure_entry = {"reason": "missing_npi", "record": record}
            failures.append(failure_entry)
            result_status = "failed"
            result_message = "missing_npi"
            output_snapshot = failure_entry
            structured_log(
                logger,
                "record_missing_npi",
                stage=StageName.MONDAY_STATUS.value,
                task_id=metadata.task_id,
                record=record,
            )
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.MONDAY_STATUS,
                npi="unknown",
                status="failed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=failure_entry,
                message=result_message,
            )
            continue

        try:
            structured_log(
                logger,
                "record_start",
                stage=StageName.MONDAY_STATUS.value,
                task_id=metadata.task_id,
                npi=npi,
            )

            if record_status in {"2", "5"}:
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
                    if record_status == "2":
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

                    elif record_status == "5":

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
                            # record.status = 6
                            # db.commit()
                            output_snapshot = {"npi_number": npi, "status": "roadblock"}
                        else:
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

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.MONDAY_STATUS.value,
        "processed": processed,
        "failed": failures,
    }
    post_webhook(metadata, StageName.MONDAY_STATUS, payload)

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
