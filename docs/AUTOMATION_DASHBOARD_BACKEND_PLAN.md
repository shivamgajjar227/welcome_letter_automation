# project1-be – Automation Dashboard Implementation Plan

This playbook is for the engineer handling the backend side. It covers database schema changes, webhook ingestion, public APIs, and testing. Follow the steps in order; every section lists the files to touch.

---

## 1. Repository primer

| Purpose | Path |
| --- | --- |
| FastAPI entry | `app/main.py` |
| Automation endpoints | `app/api/api_v1/endpoints/automation_*.py` |
| Automation models | `app/models/automation/` |
| Automation DAO + services | `app/dao/automation.py`, `app/service/automation/` |
| Pydantic schemas | `app/schemas/automation.py` |
| Alembic migrations | `app/migrations/versions/` |
| Settings | `app/settings.py` |

Spin up dev environment with `poetry install` or `pip install -r requirements.txt`, `uvicorn app.main:app --reload`.

---

## 2. Database migration (Alembic)

Create a migration file `app/migrations/versions/YYYYMMDDHHMM_add_automation_dashboard_tables.py` with the following:

### 2.1 New tables

```sql
automation_stage_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES automation_tasks(id) ON DELETE CASCADE,
    celery_task_id TEXT,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at DATETIME,
    finished_at DATETIME,
    duration_ms INTEGER,
    summary_json JSON,
    attempt INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_stage_runs_task_stage ON automation_stage_runs(task_id, stage);
CREATE INDEX idx_stage_runs_status ON automation_stage_runs(status);

automation_npi_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_run_id INTEGER NOT NULL REFERENCES automation_stage_runs(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    npi TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER DEFAULT 1,
    started_at DATETIME,
    finished_at DATETIME,
    input_snapshot_json JSON,
    output_snapshot_json JSON,
    diff_json JSON,
    artifacts_json JSON,
    message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_npi_runs_task_stage_npi ON automation_npi_runs(task_id, stage, npi);
CREATE INDEX idx_npi_runs_status ON automation_npi_runs(status);

automation_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_run_id INTEGER REFERENCES automation_stage_runs(id) ON DELETE CASCADE,
    npi_run_id INTEGER REFERENCES automation_npi_runs(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    label TEXT,
    storage_url TEXT,
    metadata_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_artifacts_stage_run ON automation_artifacts(stage_run_id);

automation_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline TEXT NOT NULL,
    stage TEXT,
    window_start DATETIME NOT NULL,
    window_end DATETIME NOT NULL,
    total_runs INTEGER DEFAULT 0,
    success INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    avg_duration_ms INTEGER,
    p95_duration_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_metrics_pipeline_stage ON automation_metrics(pipeline, stage);
```

### 2.2 Existing tables

- `automation_tasks` (see `app/models/automation/task_models.py`)
  - Add columns: `celery_task_id` (`String(64)`), `pipeline` (`String(64)` default `"welcome_letter"`), `started_at`, `finished_at`, `duration_ms`, `stage_summary_json`.
- `automation_task_events`
  - Add nullable column `stage_run_id` (FK → `automation_stage_runs.id`).
- `pr_site_data`, `npi_address`
  - Add `last_task_id` (`String(36)`), `last_stage` (`String(50)`), `last_stage_updated_at` (`DateTime`).

Run `alembic revision --autogenerate` if preferred, but verify generated SQL matches the above. Apply locally: `alembic upgrade head`.

---

## 3. SQLAlchemy models

Create new files:
- `app/models/automation/stage_run.py`
- `app/models/automation/npi_run.py`
- `app/models/automation/artifact.py`
- `app/models/automation/metrics.py` (if metrics table will be populated now; otherwise add later)

Each model inherits `db.base_class.Base`. Include relationships:

```python
class AutomationStageRun(Base):
    __tablename__ = "automation_stage_runs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(36), ForeignKey("automation_tasks.id", ondelete="CASCADE"), nullable=False)
    celery_task_id = Column(String(64), nullable=True)
    stage = Column(String(50), nullable=False)
    status = Column(String(32), nullable=False)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    summary_json = Column(JSON)
    attempt = Column(Integer, default=1)

    task = relationship("AutomationTask", back_populates="stage_runs")
    npi_runs = relationship("AutomationNPIRun", back_populates="stage_run", cascade="all, delete-orphan")
    artifacts = relationship("AutomationArtifact", back_populates="stage_run", cascade="all, delete-orphan")
```

Mirror this style for `AutomationNPIRun` and `AutomationArtifact`. Update `AutomationTask` model to include:

```python
stage_runs = relationship("AutomationStageRun", back_populates="task", cascade="all, delete-orphan")
```

Backfill `AutomationTaskDAO.serialize_task` to include new fields (`celery_task_id`, `started_at`, `finished_at`, etc.).

---

## 4. Pydantic schemas

Update `app/schemas/automation.py`:

- Add `StageEventPayload`, `StageEventSummary`, `NPIEventPayload`, `ArtifactEventPayload`.
- Add response models for dashboard API:
  - `DashboardRunSummary`, `DashboardRunDetail`, `DashboardStageSummary`, `DashboardNPIRecord`, `DashboardArtifact`.

Example:

```python
class StageEventSummary(BaseModel):
    records_total: int | None = None
    records_success: int | None = None
    records_failed: int | None = None
    artifacts: list[ArtifactPayload] | None = None

class StageEventPayload(BaseModel):
    task_id: str
    celery_id: str | None = None
    stage_run_id: str | None = None
    stage: str
    event: Literal["stage_started", "stage_completed", "stage_failed"]
    status: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    summary: StageEventSummary | None = None
    message: str | None = None
    metadata: dict[str, Any] | None = None
```

For NPI events include `input_snapshot`, `output_snapshot`, `diff`, `artifacts`.

---

## 5. Webhook ingestion endpoints

### 5.1 Routing

In `app/api/api_v1/endpoints/automation_webhooks.py`:

- Add routes:
  - `@router.post("/stage-events", status_code=202)`
  - `@router.post("/npi-events", status_code=202)`
  - `@router.post("/artifacts", status_code=202)` (optional)

### 5.2 Service layer

Create helper functions in `service/automation/webhooks.py`:

- `handle_stage_event(db, payload: StageEventPayload) -> None`
  - Find/create `AutomationStageRun`.
  - Update `AutomationTask` (`status`, `started_at`, `finished_at`, `duration_ms`, `stage_summary_json`).
  - Record an `AutomationTaskEvent` referencing `stage_run_id`.
- `handle_npi_event(db, payload: NPIEventPayload) -> None`
  - Resolve stage run by `payload.stage_run_id` (fallback by `task_id` + `stage`).
  - Insert/Update `AutomationNPIRun`.
  - Update `pr_site_data` / `npi_address` when stage == `pr_site_enrichment` or `quickcap_submission`.
- `handle_artifact_event(db, payload: ArtifactEventPayload) -> None`
  - Attach artifact rows.

Backend should enforce an internal auth (API key or existing dependency). If webhooks already use a dependency, reuse it.

---

## 6. Dashboard APIs

Create new router `app/api/api_v1/endpoints/automation_dashboard.py`:

```python
router = APIRouter(prefix="/automation/dashboard", tags=["automation-dashboard"])
```

Endpoints:

1. `GET /runs`
   - Query params: `status`, `stage`, `from`, `to`, `limit`, `offset`.
   - Return `DashboardRunListResponse` (total + items).
   - Each item includes `task_id`, `pipeline`, `status`, `started_at`, `finished_at`, `duration_ms`, stage summary counts (`success`, `failed`, `pending`), latest message.

2. `GET /runs/{task_id}`
   - Return stage timeline: stage order, status, duration, summary, artifact counts, plus recent events.

3. `GET /runs/{task_id}/npis/{npi}`
   - Return chronological list of `AutomationNPIRun` entries, diff, artifacts, plus the latest `pr_site_data` / `npi_address` snapshot for context.

4. `GET /npis`
   - Search across runs. Filters: `stage`, `status`, `health_plan`, `city`, `state`, `limit`, `offset`.
   - Provide aggregated info (last run, last stage, last message).

5. `POST /tasks/{task_id}/retry` (optional if retry scope is being implemented now)
   - Validate `task_id` exists, create new automation task record via `AutomationTaskDAO.enqueue_task`.

Expose router in `app/api/api_v1/api.py` by including it inside `automation_router`.

---

## 7. DAO & service updates

- Extend `AutomationTaskDAO`:
  - New methods `get_stage_runs(task_id)`, `get_npi_runs(task_id, npi)`, `list_runs(...)`, `summarise_runs(...)`.
  - Update `create_task`, `update_task_status` to accept `celery_task_id`, `started_at`, `finished_at`.

- Add new service module `service/automation/dashboard.py`:
  - `list_runs(db, filters) -> dict`
  - `get_run_detail(db, task_id) -> dict`
  - `get_npi_history(db, task_id, npi) -> dict`
  - `search_npis(db, filters) -> dict`

Reuse the DAO methods; structure responses matching schemas.

---

## 8. Settings & feature flag

- In `app/settings.py`, add:
  ```python
  automation_dashboard_enabled: bool = Field(False, env="AUTOMATION_DASHBOARD_ENABLED")
  automation_stage_events_api_key: Optional[str] = Field(None, env="STAGE_EVENTS_API_KEY")
  automation_npi_events_api_key: Optional[str] = Field(None, env="NPI_EVENTS_API_KEY")
  ```
- Update dependency (e.g., `app/api/dependencies.py`) to check the flag and API key for webhook endpoints.
- Document new env vars in README or `.env.example`.

---


## 9. Reference payloads

Store sample JSON files under `app/tests/fixtures/automation/`:

```json
// stage_event.json
{
  "task_id": "123",
  "celery_id": "abc",
  "stage_run_id": "stage-1",
  "stage": "monday_ingest",
  "event": "stage_completed",
  "status": "completed",
  "started_at": "2025-03-05T01:23:00Z",
  "finished_at": "2025-03-05T01:24:11Z",
  "duration_ms": 71000,
  "summary": {
    "records_total": 85,
    "records_success": 85,
    "records_failed": 0
  }
}
```

```json
// npi_event.json
{
  "task_id": "123",
  "stage_run_id": "stage-2",
  "stage": "quickcap_submission",
  "npi": "1558666615",
  "status": "completed",
  "attempt": 1,
  "input_snapshot": {"network": "Global"},
  "output_snapshot": {"address_updates": []},
  "diff": {"status": {"from": "pending", "to": "submitted"}},
  "artifacts": [
    {"type": "screenshot", "label": "success_1558666615", "url": "https://..."}
  ]
}
```

