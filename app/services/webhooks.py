from __future__ import annotations

import logging
from typing import Any, Dict

import task_tracking
from app.schemas import MondayWebhookPayload, StageResultPayload, TaskStatusPayload

logger = logging.getLogger(__name__)


def handle_monday_payload(payload: MondayWebhookPayload) -> None:
    # Currently log-only per requirements; extend to persist records as needed.
    for record in payload.records:
        logger.debug(
            "Monday record", extra={"task_id": payload.task_id, "npi": record.npi_number, "health_plan": record.health_plan}
        )


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
    logger.info(
        "Received stage payload",
        extra={
            "task_id": payload.task_id,
            "stage": payload.stage,
            "processed": len(payload.processed or payload.records or []),
            "failed": len(payload.failed or []),
        },
    )
    # Extend here to persist payload data if required.
