from __future__ import annotations

import logging
from typing import Dict, Optional

from fastapi import HTTPException, status

import task_tracking
from runner.context import StageName
from celery_app import celery_app

logger = logging.getLogger(__name__)

SUPPORTED_STAGE_TASKS = {
    StageName.MONDAY.value: "tasks.run_monday",
    StageName.MONDAY_STATUS.value: "tasks.run_monday_status",
    StageName.PR_SITE.value: "tasks.run_pr_site",
    StageName.QUICKCAP.value: "tasks.run_quickcap",
    "pipeline": "tasks.run_pipeline",
}


def enqueue_task(stage: str, metadata: Optional[Dict] = None) -> Dict:
    stage = stage or StageName.MONDAY.value
    if stage not in SUPPORTED_STAGE_TASKS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported stage '{stage}'")

    logger.info("Creating task for stage '%s' with metadata=%s", stage, metadata)
    task_record = task_tracking.create_task(stage, metadata)

    try:
        task_name = SUPPORTED_STAGE_TASKS[stage]
        celery_task = celery_app.send_task(task_name, args=[task_record.id, metadata or {}])
    except Exception as exc:
        logger.exception("Failed to enqueue Celery task for task_id=%s stage=%s", task_record.id, stage)
        # re-raise as HTTPException so FastAPI emits a structured 500 response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue task. Check worker/broker logs.",
        ) from exc

    logger.info("Enqueued Celery task", extra={"task_id": task_record.id, "celery_id": celery_task.id, "stage": stage})
    return {"task_id": task_record.id, "celery_id": celery_task.id}


def fetch_task(task_id: str) -> Dict:
    task = task_tracking.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task_tracking.serialize_task(task)


def fetch_tasks(limit: int = 50, offset: int = 0, status_filter: Optional[str] = None) -> Dict:
    listing = task_tracking.list_tasks(limit=limit, offset=offset, status=status_filter)
    return listing


def fetch_events(task_id: str) -> Dict:
    return task_tracking.list_events(task_id)
