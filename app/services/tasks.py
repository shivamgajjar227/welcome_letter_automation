from __future__ import annotations

from typing import Dict, Optional

from fastapi import HTTPException, status

import task_tracking
from runner.context import StageName
from tasks import run_monday, run_pipeline

SUPPORTED_STAGES = {
    StageName.MONDAY.value: run_monday,
    "pipeline": run_pipeline,
}


def enqueue_task(stage: str, metadata: Optional[Dict] = None) -> Dict:
    stage = stage or StageName.MONDAY.value
    if stage not in SUPPORTED_STAGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported stage '{stage}'")

    task_record = task_tracking.create_task(stage, metadata)

    celery_task = SUPPORTED_STAGES[stage].delay(task_record.id, metadata or {})

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
