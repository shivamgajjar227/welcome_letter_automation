"""Headless runner implementation for updating Monday board statuses."""

from __future__ import annotations

import logging
import time
from typing import Dict, List

from selenium.webdriver.remote.webdriver import WebDriver

from pages.monday_page import MondayPage
from pages.monday_status_page import MondayStatusPage
from .. import artifacts
from ..context import RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook, fetch_stage_payload

logger = logging.getLogger(__name__)

def safe_str(value: Any) -> str:
    """Safely convert value to string, handling None."""
    return str(value) if value is not None else ""

def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    stage_result = StageResult(stage=StageName.MONDAY_STATUS)
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
        status = safe_str(record.get("status"))
        health_plan = safe_str(record.get("health_plan"))
        effective_date = safe_str(record.get("effective_date"))
        lines_of_business = safe_str(record.get("lines_of_business"))
        remarks = safe_str(record.get("remarks"))
        city = safe_str(record.get("city"))

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

            if status == "2" or status == "5":
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
                            matched_health_plan = monday_health_plan
                            break

                if health_plan_match:
                    if status == "2":
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

                        print(f" NPI {npi} processed as Done.")

                    elif status == "5":

                        if remarks:
                            remarks_text = remarks
                            print(f" Found remarks in DB for NPI {npi}: {remarks_text}")
                        else:
                            remarks_text = "Organisation Data Missing"
                            print(
                                f"⚠No remarks found in DB for NPI {npi}, using default")


                        remarks_added = monday_page.process_rows_and_enter_remarks(
                            db_health_plan=health_plan,
                            db_effective_date=effective_date,
                            remarks_text=remarks_text
                        )

                        if remarks_added:
                            print(f" Remarks added to matching rows for NPI {npi}")
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
                        else:
                            print(f" No matching rows found for NPI {record.npi_number}")
                    else:
                        print(f"No remarks found in DB for NPI {record.npi_number}")
                else:
                    if monday_health_plans:
                        monday_plans_str = ", ".join(monday_health_plans)
                    else:
                        monday_plans_str = "No health plans found in UI"
                    print(
                        f"Skipping NPI {npi} - Health plan mismatch. DB: {health_plan}, Monday.com: {monday_plans_str}")
                    processed.append({"npi_number": npi, "status": "done"})
                    continue

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
