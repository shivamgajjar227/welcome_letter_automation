from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import MondayWebhookPayload, StageResultPayload, TaskStatusPayload
from app.services import webhooks as webhook_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = logging.getLogger(__name__)


@router.post("/monday", summary="Receive Monday ingestion payloads")
async def receive_monday(payload: MondayWebhookPayload) -> dict:
    logger.info(
        "Received Monday ingestion payload",
        extra={"task_id": payload.task_id, "records": len(payload.records)},
    )
    webhook_service.handle_monday_payload(payload)
    return {"status": "logged"}


@router.post("/task-status", summary="Receive Celery task status updates")
async def receive_task_status(payload: TaskStatusPayload) -> dict:
    try:
        webhook_service.handle_task_status(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/monday-status", summary="Receive Monday status update results")
async def receive_monday_status(payload: StageResultPayload) -> dict:
    webhook_service.handle_stage_payload(payload)
    return {"status": "ok"}


@router.post("/pr-site", summary="Receive PR Site enrichment data")
async def receive_pr_site(payload: StageResultPayload) -> dict:
    webhook_service.handle_stage_payload(payload)
    return {"status": "ok"}


@router.post("/quickcap", summary="Receive QuickCap submission data")
async def receive_quickcap(payload: StageResultPayload) -> dict:
    webhook_service.handle_stage_payload(payload)
    return {"status": "ok"}
