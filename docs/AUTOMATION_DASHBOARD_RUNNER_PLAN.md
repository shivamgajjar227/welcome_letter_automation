# Welcome Letter Runner – Dashboard Work Plan

Goal: teach any engineer (even new to this repo) how to add the telemetry hooks required for the Automation Dashboard. Work through the steps in order; links point to existing files.

---

## 1. Where things live

| Purpose | Path |
| --- | --- |
| Celery tasks entrypoints | `tasks.py` |
| Runner orchestration | `runner/headless_runner.py` |
| Stage implementations | `runner/flows/monday.py`, `runner/flows/pr_site.py`, `runner/flows/quickcap.py`, `runner/flows/monday_status.py` |
| Artifact helpers | `runner/artifacts.py` |
| Settings/env | `config.py` (+ `.env` file) |
| Docs (you are here) | `docs/` |

Clone the repo, create a virtualenv (Python 3.11+), `pip install -r requirements.txt`, and copy `.env.example` → `.env`.

---

## 2. Add the event helper (all telemetry goes through this)

1. Create `monitoring/events.py` with functions:
   - `send_pipeline_event(task_id, celery_id, status, **fields)`
   - `send_stage_event(task_id, celery_id, stage, event, payload)`
   - `send_npi_event(task_id, stage, npi, status, payload)`
2. Each helper should:
   - Read target URLs from `config.get_settings()` (`task_status_webhook_url`, `stage_events_webhook_url`, `npi_events_webhook_url` – add if missing).
   - Log and no-op when URL is absent (dev mode).
   - Use `requests.post(..., timeout=30)` and catch `RequestException` (log warning only).
3. Write unit tests in `tests/test_events.py` using `requests_mock` or `monkeypatch`.

---

## 3. Emit pipeline start/finish from Celery tasks

1. In `tasks.py`:
   - Import `monitoring.events`.
   - Inside each task (`run_monday`, `run_pr_site`, etc.) grab `celery_id = run_monday.request.id` (Celery injects `request` on bound tasks). If tasks aren’t bound yet, convert them: `@celery_app.task(bind=True, name="tasks.run_monday")`.
   - At top: `events.send_pipeline_event(task_id=current_task_id, celery_id=celery_id, status="started", stage=None)`.
   - On success/failure send `"completed"` / `"failed"` along with result summary.
2. Ensure existing `send_status_update` still runs (backend expects it). Event helper augments it, does not replace it.

---

## 4. Emit stage events in `runner/headless_runner.py`

1. Right before stage execution loop:
   ```python
   stage_run_id = uuid.uuid4().hex
   events.send_stage_event(task_id=result.task_id, celery_id=metadata.celery_id, stage=stage.value, event="started", ...)
   ```
2. Measure duration:
   ```python
   started_at = time.time()
   ...
   duration_ms = int((time.time() - started_at) * 1000)
   ```
3. On success send `event="completed"` with summary (`records_total`, `records_failed`, artifact count). On exception send `event="failed"` and re-raise.
4. Store `stage_run_id` and timing info back into `StageResult` so later stages / logs can reuse it.

---

## 5. Emit per-NPI events inside each stage file

Do the same pattern in every `runner/flows/*.py`:

1. Extract incoming records (e.g., `metadata.request_payload`, `fetch_stage_payload`). For each NPI:
   - Send `events.send_npi_event(..., status="in_progress", input_snapshot=record)`.
2. After success:
   - Build `output_snapshot` (what we POST to webhooks or write to JSON).
   - Collect artifact URLs (screenshots returned by `artifacts.capture_*` now include `public_url`).
   - Send final event `status="completed"` and include `diff` if applicable.
3. On exceptions:
   - Catch, send `status="failed"` with `message=str(exc)` and artifact references (failure screenshot/DOM dump), then re-raise to keep current behaviour.

Repeat for:
- `runner/flows/monday.py` (records fetched)
- `runner/flows/pr_site.py` (enriched data + failures)
- `runner/flows/quickcap.py` (submissions + retries)
- `runner/flows/monday_status.py` (board updates & remarks)

---

## 6. Expose webhook URLs via settings

1. In `config.py`, ensure the following settings exist (defaults shown for local dev):
   ```python
   stage_events_webhook_url: Optional[str] = Field(
       "http://0.0.0.0:10022/api/automation/webhooks/stage-events", env="STAGE_EVENTS_WEBHOOK_URL"
   )
   npi_events_webhook_url: Optional[str] = Field(
       "http://0.0.0.0:10022/api/automation/webhooks/npi-events", env="NPI_EVENTS_WEBHOOK_URL"
   )
   artifact_events_webhook_url: Optional[str] = Field(
       "http://0.0.0.0:10022/api/automation/webhooks/artifacts", env="ARTIFACT_EVENTS_WEBHOOK_URL"
   )
   artifact_base_url: Optional[str] = Field(None, env="ARTIFACT_BASE_URL")
   ```
2. Update `.env.example` with placeholders (point to backend dev server, e.g., `http://localhost:8000/api/automation/webhooks/stage-events`).
3. Make sure `get_settings()` caches the new fields and they’re used by `monitoring/events.py`.

---

## 7. Artifacts need public URLs

1. Update `runner/artifacts.py` so each helper returns a `ArtifactRecord` including `public_url`. For local dev it can be `f"{settings.media_base_url}/{relative_path}"`.
2. When sending events, always include `artifact.public_url` (skip if missing).

---
