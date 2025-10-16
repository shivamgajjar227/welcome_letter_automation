"""
Utility helpers for managing automation task state in MariaDB.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from sqlalchemy.orm import Session

from db.session import SessionLocal, engine
from models.task_models import AutomationTask, AutomationTaskEvent

_TABLES_INITIALISED = False


def ensure_tables() -> None:
    global _TABLES_INITIALISED
    if _TABLES_INITIALISED:
        return
    AutomationTask.__table__.create(bind=engine, checkfirst=True)
    AutomationTaskEvent.__table__.create(bind=engine, checkfirst=True)
    _TABLES_INITIALISED = True


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    ensure_tables()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def serialize_task(task: AutomationTask) -> Dict[str, Any]:
    return {
        "id": task.id,
        "stage": task.stage,
        "status": task.status,
        "metadata": task.metadata_dict(),
        "result": task.result_dict(),
        "message": task.message,
        "attempt_count": task.attempt_count,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def create_task(stage: str, metadata: Optional[Dict[str, Any]] = None) -> AutomationTask:
    with session_scope() as session:
        task = AutomationTask(stage=stage)
        if metadata:
            task.set_metadata(metadata)
        session.add(task)
        session.flush()
        session.refresh(task)
        session.add(AutomationTaskEvent(task_id=task.id, status="created", detail=json.dumps(metadata or {})))
        return task


def update_task_status(
    task_id: str,
    status: str,
    *,
    result: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    attempt_delta: int = 0,
    event_detail: Optional[Dict[str, Any]] = None,
) -> Optional[AutomationTask]:
    with session_scope() as session:
        task = session.get(AutomationTask, task_id)
        if not task:
            return None
        task.status = status
        if message:
            task.message = message
        if result:
            task.set_result(result)
        if attempt_delta:
            task.attempt_count = (task.attempt_count or 0) + attempt_delta
        session.add(task)
        session.add(
            AutomationTaskEvent(
                task_id=task.id,
                status=status,
                detail=json.dumps(event_detail or result or {}, default=str),
            )
        )
        session.flush()
        session.refresh(task)
        return task


def get_task(task_id: str) -> Optional[AutomationTask]:
    with session_scope() as session:
        return session.get(AutomationTask, task_id)


def list_tasks(limit: int = 50, offset: int = 0, status: Optional[str] = None) -> Dict[str, Any]:
    with session_scope() as session:
        query = session.query(AutomationTask).order_by(AutomationTask.created_at.desc())
        if status:
            query = query.filter(AutomationTask.status == status)
        total = query.count()
        tasks = query.offset(offset).limit(limit).all()
        return {
            "total": total,
            "items": [serialize_task(task) for task in tasks],
        }


def list_events(task_id: str) -> Dict[str, Any]:
    with session_scope() as session:
        events = (
            session.query(AutomationTaskEvent)
            .filter(AutomationTaskEvent.task_id == task_id)
            .order_by(AutomationTaskEvent.created_at)
            .all()
        )
        return {
            "task_id": task_id,
            "events": [
                {
                    "status": event.status,
                    "detail": json.loads(event.detail) if event.detail else None,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ],
        }
