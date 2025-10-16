import datetime as dt
import json
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from db.base_class import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


class AutomationTask(Base):
    __tablename__ = "automation_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    stage = Column(String(50), nullable=False)
    status = Column(String(32), nullable=False, default="created")
    metadata = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    events = relationship("AutomationTaskEvent", back_populates="task", cascade="all, delete-orphan")

    def set_metadata(self, payload: Dict[str, Any]) -> None:
        self.metadata = json.dumps(payload, default=str)

    def set_result(self, payload: Dict[str, Any]) -> None:
        self.result = json.dumps(payload, default=str)

    def metadata_dict(self) -> Optional[Dict[str, Any]]:
        if not self.metadata:
            return None
        return json.loads(self.metadata)

    def result_dict(self) -> Optional[Dict[str, Any]]:
        if not self.result:
            return None
        return json.loads(self.result)


class AutomationTaskEvent(Base):
    __tablename__ = "automation_task_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey("automation_tasks.id"), nullable=False, index=True)
    status = Column(String(32), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    task = relationship("AutomationTask", back_populates="events")

