from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas import MondayWebhookPayload, TaskStatusPayload
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
