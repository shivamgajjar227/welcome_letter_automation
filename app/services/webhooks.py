from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import task_tracking
from app.schemas import MondayWebhookPayload, StageResultPayload, TaskStatusPayload
from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from runner.context import StageName

logger = logging.getLogger(__name__)


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def handle_monday_payload(payload: MondayWebhookPayload) -> None:
    session = SessionLocal()
    try:
        for record in payload.records:
            npi = _to_int(record.npi_number)
            if npi is None:
                logger.warning("Skipping Monday record with invalid NPI", extra={"record": record.model_dump()})
                continue

            obj = session.query(PRSiteData).filter(PRSiteData.npi_number == npi).one_or_none()
            if not obj:
                obj = PRSiteData(npi_number=npi)
                session.add(obj)

            obj.effective_date = record.effective_date
            obj.health_plan = record.health_plan
            obj.lines_of_business = record.lines_of_business
            obj.status = 0
            obj.updated_at = datetime.utcnow()
        session.commit()
    except Exception:  # pragma: no cover - DB exceptions
        session.rollback()
        logger.exception("Failed to persist Monday records")
        raise
    finally:
        session.close()


def handle_task_status(payload: TaskStatusPayload) -> None:
    task = task_tracking.update_task_status(
        payload.task_id,
        payload.status,
        result=payload.result,
        message=payload.message,
        event_detail={"stage": payload.stage} if payload.stage else None,
    )
    if not task:
        logger.error("Task status update received for unknown task_id=%s", payload.task_id)
        raise ValueError("Unknown task_id")
    logger.info(
        "Updated task status",
        extra={"task_id": payload.task_id, "status": payload.status, "stage": payload.stage},
    )


def handle_stage_payload(payload: StageResultPayload) -> None:
    if not payload.stage:
        logger.warning("Stage payload missing stage value", extra={"task_id": payload.task_id})
        return
    try:
        stage = StageName(payload.stage)
    except ValueError:
        logger.warning("Unknown stage payload received", extra={"stage": payload.stage})
        return

    if stage == StageName.PR_SITE:
        _update_pr_site_records(payload)
    elif stage == StageName.QUICKCAP:
        _update_quickcap_records(payload)
    elif stage == StageName.MONDAY_STATUS:
        _update_monday_status(payload)


def _update_pr_site_records(payload: StageResultPayload) -> None:
    records = payload.records or payload.processed or []
    if not records:
        return
    session = SessionLocal()
    try:
        for record in records:
            npi = _to_int(record.get("npi_number"))
            if npi is None:
                continue
            obj = session.query(PRSiteData).filter(PRSiteData.npi_number == npi).one_or_none()
            if not obj:
                obj = PRSiteData(npi_number=npi)
                session.add(obj)

            obj.last_name = record.get("last_name") or obj.last_name
            obj.first_name = record.get("first_name") or obj.first_name
            obj.gender = record.get("gender") or obj.gender
            obj.city = record.get("city") or obj.city
            obj.state = record.get("state") or obj.state
            obj.zip_code = record.get("zip_code") or obj.zip_code
            obj.category = record.get("category") or obj.category
            obj.speciality = record.get("speciality") or obj.speciality
            obj.network = record.get("network") or obj.network
            obj.taxonomy_code = record.get("taxonomy_code") or obj.taxonomy_code
            obj.status = 1
            obj.updated_at = datetime.utcnow()
        session.commit()
    except Exception:  # pragma: no cover
        session.rollback()
        logger.exception("Failed to update PR Site records")
        raise
    finally:
        session.close()


def _update_quickcap_records(payload: StageResultPayload) -> None:
    records = payload.processed or []
    if not records:
        return
    session = SessionLocal()
    try:
        for record in records:
            npi = _to_int(record.get("npi_number"))
            if npi is None:
                continue
            obj = session.query(PRSiteData).filter(PRSiteData.npi_number == npi).one_or_none()
            if obj:
                obj.status = 2
                obj.updated_at = datetime.utcnow()
        session.commit()
    except Exception:  # pragma: no cover
        session.rollback()
        logger.exception("Failed to update QuickCap records")
        raise
    finally:
        session.close()


def _update_monday_status(payload: StageResultPayload) -> None:
    records = payload.processed or []
    if not records:
        return
    session = SessionLocal()
    try:
        for record in records:
            npi = _to_int(record.get("npi_number"))
            if npi is None:
                continue
            obj = session.query(PRSiteData).filter(PRSiteData.npi_number == npi).one_or_none()
            if obj:
                obj.status = 3
                obj.updated_at = datetime.utcnow()
        session.commit()
    except Exception:  # pragma: no cover
        session.rollback()
        logger.exception("Failed to update Monday status records")
        raise
    finally:
        session.close()
