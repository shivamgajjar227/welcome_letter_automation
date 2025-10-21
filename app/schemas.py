from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class TaskCreatePayload(BaseModel):
    stage: str = Field("monday_ingest", description="Target stage to execute")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary metadata passed to the runner")


class TaskResponse(BaseModel):
    id: str
    stage: str
    status: str
    metadata: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    attempt_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]


class TaskEventResponse(BaseModel):
    task_id: str
    events: List[Dict[str, Any]]


class MondayRecord(BaseModel):
    npi_number: str
    effective_date: str
    health_plan: str
    lines_of_business: str


class MondayWebhookPayload(BaseModel):
    task_id: str
    stage: Optional[str] = Field(default="monday_ingest")
    records: List[MondayRecord]


class ArtifactPayload(BaseModel):
    type: str
    path: str
    description: Optional[str] = None


class TaskStatusPayload(BaseModel):
    task_id: str
    status: str
    stage: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

