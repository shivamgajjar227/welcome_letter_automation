# Automation Dashboard Implementation Guide

> Use this document when you are ready to build the “celery metrix for welcome letter automation” dashboard. It breaks down the work by phase, lists the files to touch, and calls out tests and rollout steps. A lighter “what is this?” primer lives in `docs/AUTOMATION_DASHBOARD_FLOW.md`.

---

## 0. Quick Start

- **Repositories**:  
  - Runner: `welcome_letter_automation`  
  - Backend API: `project1-be`
- **Environments**: Dev, staging, prod (Redis + Celery workers + Selenium runner).  
- **Feature flag**: `AUTOMATION_DASHBOARD_ENABLED` (add if not present) guards new UI + APIs.
- **Branch naming**: `feat/automation-dashboard-*`

---

## 1. Phase-by-Phase Plan

### Phase 1 – Instrument the Runner

| Task | File(s) | Notes |
| --- | --- | --- |
| Create event helper | `welcome_letter_automation/monitoring/events.py` | Wrap `requests.post`, add retry/backoff, and shape payloads. |
| Emit pipeline events | `welcome_letter_automation/tasks.py` | Pull `self.request.id` inside each Celery task and pass to helper (`pipeline_started`, `pipeline_completed`, `pipeline_failed`). |
| Emit stage lifecycle | `welcome_letter_automation/runner/headless_runner.py` | Before `impl(driver, metadata)` call `events.stage_started(...)`; on success/failure send completion events with duration. |
| Emit NPI progress | `runner/flows/*.py` | For Monday, PR Site, QuickCap, Monday Status emit `npi_progress` events (start, success, failure). Include `task_id`, `stage`, `npi`, `input_snapshot`, `output_snapshot`, `artifacts`. |
| Centralise URLs | `welcome_letter_automation/config.py` | Add `stage_events_webhook_url`, `npi_events_webhook_url`, `artifact_upload_url`. Default to `None`, log locally when unset. |
| Artifact metadata | `welcome_letter_automation/runner/artifacts.py` | Ensure helpers return both relative paths and `public_url` (if S3/local static). Include in event payloads. |

**Developer checklist**
1. Scaffold `monitoring/events.py` with typed helper functions (`send_stage_event`, `send_npi_event`, `send_artifact_event`).  
2. Update each Celery task (`run_monday`, `run_pr_site`, …) to pass `task_id` + `celery_id` to the helper.  
3. Ensure exceptions call `events.stage_failed` before re-raising.  
4. Add unit tests (pytest) around the helper module (mock `requests.post`).  
5. Ship new `.env` sample keys.

### Phase 2 – Persist data in `project1-be`

1. **Alembic migration** (`project1-be/app/migrations/versions/XXXXXXXX_dashboard_tables.py`)
   - Tables: `automation_stage_runs`, `automation_npi_runs`, `automation_artifacts`, `automation_metrics`.
   - Alter `automation_tasks` to add `celery_task_id`, `pipeline`, `started_at`, `finished_at`, `duration_ms`, `stage_summary_json`.
   - Add `last_task_id`, `last_stage`, `last_stage_updated_at` to `pr_site_data` and `npi_address`.

2. **SQLAlchemy models**
   - `app/models/automation/stage_run.py` (new).  
   - `app/models/automation/npi_run.py` (new).  
   - `app/models/automation/artifact.py` (new).  
   - Update `task_models.py`, `pr_site_data.py`, `npi_address.py` to match migrations.

3. **DAO layer**
   - Extend `dao/automation.py` with helpers:
     - `record_stage_event(...)`
     - `record_npi_event(...)`
     - `record_artifacts(...)`
     - `hydrate_task_summary(...)`

4. **Webhook endpoints**
   - `app/api/api_v1/endpoints/automation_webhooks.py`: add routers for `/stage-events`, `/npi-events`, `/artifacts`.  
   - Create Pydantic schemas in `app/schemas/automation.py`: `StageEventPayload`, `NPIEventPayload`, `ArtifactPayload`.
   - Wire service layer (`service/automation/webhooks.py`) to insert into DAO and update `pr_site_data` / `npi_address` copies.

5. **Read endpoints for dashboard**
   - `app/api/api_v1/endpoints/automation_dashboard.py` (new).  
   - Service module `service/automation/dashboard.py` that composes data (tasks + stages + npis + artifacts).  
   - Response schemas `DashboardRunListResponse`, `DashboardRunDetailResponse`, `DashboardNPIHistoryResponse`.

6. **Settings + feature flag**
   - `app/settings.py`: add `AUTOMATION_DASHBOARD_ENABLED: bool`.  
   - Guard new endpoints using dependency that checks the flag.

7. **Tests**
   - SQLAlchemy migrations test (run upgrade + downgrade).  
   - Webhook ingestion tests (use `TestClient` and a fixture DB).  
   - Dashboard query tests verifying filtering and pagination.



---

## 2. Implementation Details

### 2.1 Stage Event payload structure

```json
{
  "task_id": "task-uuid",
  "celery_id": "celery-uuid",
  "stage_run_id": "stage-uuid",
  "stage": "monday_ingest",
  "event": "stage_completed",
  "started_at": "2025-03-05T01:23:00Z",
  "finished_at": "2025-03-05T01:24:11Z",
  "duration_ms": 71000,
  "success": true,
  "summary": {
    "records_total": 85,
    "records_success": 85,
    "records_failed": 0
  },
  "artifacts": [
    {"type": "screenshot", "label": "board_loaded", "url": "https://..."}
  ],
  "metadata": {"headless": true}
}
```

### 2.2 NPI Event payload structure

```json
{
  "task_id": "task-uuid",
  "stage_run_id": "stage-uuid",
  "stage": "quickcap_submission",
  "npi": "1558666615",
  "status": "completed",
  "attempt": 1,
  "input_snapshot": {"network": "Global", "health_plan": "Aetna PPO"},
  "output_snapshot": {"address_updates": [...]},
  "diff": {"status": {"from": "pending", "to": "submitted"}},
  "artifacts": [{"type": "screenshot", "label": "success_1558666615", "url": "https://..."}],
  "message": null
}
```

### 2.3 REST endpoints

| Endpoint | Purpose | Auth |
| --- | --- | --- |
| `POST /api/automation/webhooks/stage-events` | Ingest stage lifecycle | Internal token |
| `POST /api/automation/webhooks/npi-events` | Ingest per-NPI updates | Internal token |
| `POST /api/automation/webhooks/artifacts` | (Optional) upload artifact metadata | Internal token |
| `GET /api/automation/dashboard/runs` | List runs with summary stats | Authenticated user, `AUTOMATION_DASHBOARD_ENABLED` |
| `GET /api/automation/dashboard/runs/{task_id}` | Detailed view | Same as above |
| `GET /api/automation/dashboard/runs/{task_id}/npis/{npi}` | NPI timeline | Same |
| `GET /api/automation/dashboard/npis` | Cross-run search | Same |
| `POST /api/automation/tasks/{task_id}/retry` | Retry entry point (optional) | Same |

All timestamps are ISO 8601 (UTC). Numerical durations use milliseconds.

---

## 3. Database Summary

| Table | Columns (high level) | Notes |
| --- | --- | --- |
| `automation_stage_runs` | `id`, `task_id`, `stage`, `status`, `celery_id`, `started_at`, `finished_at`, `duration_ms`, `summary_json` | Index on `(task_id, stage)` + `(status)` |
| `automation_npi_runs` | `id`, `stage_run_id`, `task_id`, `npi`, `status`, `attempt`, `input_snapshot_json`, `output_snapshot_json`, `diff_json`, `message`, `started_at`, `finished_at` | Composite index `(task_id, stage, npi)` |
| `automation_artifacts` | `id`, `stage_run_id`, `npi_run_id`, `type`, `label`, `storage_url`, `metadata_json`, `created_at` | Nullable `npi_run_id` for stage-level artifacts |
| `automation_metrics` | `id`, `pipeline`, `stage`, `window_start`, `window_end`, `total_runs`, `success`, `failed`, `avg_duration_ms`, `p95_duration_ms` | Batch job fills this (daily/hourly) |
| `automation_tasks` (existing) | + `celery_task_id`, `pipeline`, `started_at`, `finished_at`, `duration_ms`, `stage_summary_json` | Backfill existing records with `NULL` |
| `pr_site_data` / `npi_address` | + `last_task_id`, `last_stage`, `last_stage_updated_at` | Use for quick filters in dashboard |



