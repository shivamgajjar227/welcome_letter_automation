from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import (
    TaskCreatePayload,
    TaskEventResponse,
    TaskListResponse,
    TaskResponse,
)
from app.services import tasks as task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreatePayload) -> TaskResponse:
    task_ref = task_service.enqueue_task(payload.stage, payload.metadata or {})
    task = task_service.fetch_task(task_ref["task_id"])
    return TaskResponse(**task)


@router.get("", response_model=TaskListResponse)
def list_tasks(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), status: str | None = None):
    data = task_service.fetch_tasks(limit=limit, offset=offset, status_filter=status)
    return TaskListResponse(**data)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str) -> TaskResponse:
    task = task_service.fetch_task(task_id)
    return TaskResponse(**task)


@router.get("/{task_id}/events", response_model=TaskEventResponse)
def get_task_events(task_id: str) -> TaskEventResponse:
    events = task_service.fetch_events(task_id)
    return TaskEventResponse(**events)

