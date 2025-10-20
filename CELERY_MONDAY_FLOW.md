# Celery Monday Flow – Detailed Walkthrough

This document explains how a Monday ingestion task travels from `tasks.py` through the headless runner (`runner/flows/monday.py`) so that developers can maintain the existing flow and use it as a template for future stages (PR Site, QuickCap, etc.).

## Overview
1. FastAPI receives a `POST /tasks` request (e.g., `{"stage": "monday_ingest"}`) and persists a task record.
2. FastAPI enqueues the job by calling `tasks.run_monday.delay(task_id, payload)`.
3. Celery worker picks up the task, constructs `RunnerMetadata`, and executes `run_headless_flow`.
4. The headless runner drives the Monday.com Selenium flow and posts collected NPIs to the configured webhook (`MONDAY_INGEST_API_URL`).
5. Task state is updated (`task_tracking.update_task_status`) to reflect success or failure.

## Step-by-Step Execution

### 1. Task Enqueue (`tasks.py`)
```python
@celery_app.task(name="tasks.run_monday")
def run_monday(task_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> dict:
    metadata = build_metadata(enabled_stages=[StageName.MONDAY])
    _ensure_stage_enabled(metadata, StageName.MONDAY)
    if task_id:
        metadata.task_id = task_id
    if payload:
        metadata.request_payload = payload
    task_tracking.update_task_status(task_id or metadata.task_id, "in_progress", attempt_delta=1)
    try:
        result = run_headless_flow(metadata)
    except Exception as exc:
        task_tracking.update_task_status(
            task_id or metadata.task_id,
            "failed",
            message=str(exc),
        )
        raise
    stage = result.stages.get(StageName.MONDAY)
    task_tracking.update_task_status(
        task_id or result.task_id,
        "completed" if stage and stage.success else "failed",
        result={"monday": stage.data if stage else {}},
    )
    return {"task_id": result.task_id, "success": bool(stage and stage.success), "data": stage.data if stage else {}}
```
**Key points:**
- `build_metadata` pulls credentials/URLs from `config.py` (Pydantic settings) and includes a `webhook_url` if `MONDAY_INGEST_API_URL` is set.
- Task state is recorded in MariaDB via `task_tracking.update_task_status` (in-progress → completed/failed).

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
- On success: `RunnerResult` holds artifacts and `stage_result.data`; Celery task returns `{"success": true, ...}`.
- On error: Exceptions propagate, `task_tracking` marks status `failed`, and the worker logs details (worker name, stage, error message).

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
