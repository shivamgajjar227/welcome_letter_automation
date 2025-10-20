# Celery Monday Flow – Detailed Walkthrough

This document explains how a Monday ingestion task travels from `tasks.py` through the headless runner (`runner/flows/monday.py`) so that developers can maintain the existing flow and use it as a template for future stages (PR Site, QuickCap, etc.).

## Overview
1. FastAPI receives a `POST /tasks` request (e.g., `{"stage": "monday_ingest"}`) and persists a task record.
2. FastAPI enqueues the job by calling `tasks.run_monday.delay(task_id, payload)`.
3. Celery worker picks up the task, constructs `RunnerMetadata`, and executes `run_headless_flow`.
4. The headless runner drives the Monday.com Selenium flow and posts collected NPIs to the configured webhook (`MONDAY_INGEST_API_URL`).
5. Celery sends lifecycle events (`in_progress`, `completed`, `failed`) to FastAPI via `TASK_STATUS_WEBHOOK_URL`, allowing the API to persist status in MariaDB.

## Step-by-Step Execution

### 1. Task Enqueue (`tasks.py`)
```python
@celery_app.task(name="tasks.run_monday")
def run_monday(...):
    current_task_id = task_id or metadata.task_id
    send_status_update(current_task_id, "in_progress", stage="monday_ingest")
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        send_status_update(current_task_id, "failed", stage="monday_ingest", message=str(exc))
        raise
    send_status_update(
        current_task_id,
        "completed" if stage and stage.success else "failed",
        stage="monday_ingest",
        result={"data": stage.data, "artifacts": [...]},
    )
```
**Key points:**
- `build_metadata` pulls credentials/URLs from `config.py` (Pydantic settings) and includes a `webhook_url` if `MONDAY_INGEST_API_URL` is set.
- `send_status_update` posts task lifecycle events to FastAPI (`TASK_STATUS_WEBHOOK_URL`), removing the need for Celery to touch the database.

### 2. Metadata Construction (`tasks.py`)
```python
def build_metadata(enabled_stages: Iterable[StageName]) -> RunnerMetadata:
    ...
    if stage == StageName.MONDAY and settings.monday_ingest_api_url:
        cfg.extra["webhook_url"] = settings.monday_ingest_api_url
```
**Purpose:** Provide the runner with Selenium settings (URLs, credentials) and any extra details (e.g., the webhook endpoint).

### 3. Headless Runner Orchestration (`runner/headless_runner.py`)
```python
StageName.MONDAY -> monday.run(driver, metadata)
```
- `run_headless_flow` opens a browser session (`runner/browser.py`), iterates stages, and stops on the first failure.
- Artifacts (screenshots, HTML, JSON) are saved using `runner/artifacts.py`.

### 4. Monday Flow (`runner/flows/monday.py`)
```python
structured_log(... "stage_start" ...)
if monday_page.is_login_page():
    monday_page.login(...)
monday_page.click_welcome_letter_qc()
npis = monday_page.get_pr_site_npis()
if not npis:
    stage_result.mark_finished(success=True)
    return stage_result
_send_records_to_api(npis, metadata)
```
**Functionality matches `tests/quickcap_suite.py::test_monday`:**
- Authenticate only when the login form is present.
- Click "Welcome Letter QC" and collect NPIs with status "Not Started".
- Instead of inserting into the DB, call `_send_records_to_api` to post records to the webhook.

### 5. Webhook (New `api_proxy.py`)
```python
@app.post("/webhooks/monday")
async def monday_webhook(request: Request):
    payload = await request.json()
    # log payload for debugging (JSONL file)
```
- Acts as a debugging proxy—you can inspect `proxy_logs.jsonl` or hit `GET /logs` to review received payloads.
- Replace with your FastAPI endpoint once ready to persist records to MariaDB.

### 6. Task Completion
- On success: `RunnerResult` holds artifacts and `stage_result.data`; Celery task returns `{"success": true, ...}` and notifies FastAPI.
- On error: Exceptions propagate, `send_status_update(..., "failed")` captures the failure, and the worker logs details (worker name, stage, error message).

## How to Extend for PR Site / QuickCap
1. **Create a flow module** (e.g., `runner/flows/pr_site.py`) following the Monday pattern:
   - Accept `WebDriver` + `RunnerMetadata`.
   - Add logging at each step (`structured_log`).
   - Capture artifacts (screenshots, DOM snapshots, JSON results).
   - Call a helper to send data to FastAPI via REST (no direct DB access).
2. **Update `build_metadata`** to inject necessary creds/URLs and webhook endpoints for the new stage.
3. **Register a Celery task** (`tasks.run_pr_site`, etc.) that mirrors `run_monday`—call `run_headless_flow`, handle exceptions, update status.
4. **Add FastAPI endpoints/webhooks** to receive the new payloads, persist to DB, and return appropriate responses.
5. **Keep logging consistent:** INFO by default, DEBUG when `TASKS_LOG_LEVEL=DEBUG` to capture more granular details.

With this template, developers can replicate the pattern for additional pipelines while keeping code approachable.
