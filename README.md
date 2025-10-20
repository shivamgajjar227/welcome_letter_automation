gi# Welcome Letter Automation – Headless Runner Platform

This repository automates the Monday → PR Site → QuickCap workflow using headless Selenium, Celery task orchestration, and a FastAPI management API. The current production-ready path focuses on the Monday ingestion stage, with PR Site and QuickCap scaffolds in place for future expansion.

## Components Overview

| Area | Path | Purpose |
| --- | --- | --- |
| Runner core | `runner/` | Reusable headless Selenium utilities (context models, browser factory, artifact capture, structured logging) and stage-specific flows. |
| Celery tasks | `tasks.py` | Builds stage metadata from environment variables, triggers the headless runner, and reports status via REST webhooks. |
| Task tracking | FastAPI (`models/task_models.py`, `task_tracking.py`) | Persists automation task lifecycle (`automation_tasks`, `automation_task_events`) when webhook updates arrive. |
| FastAPI | `app/` | REST endpoints (`POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `/tasks/{id}/events`) exposing task management features. |
| Kubernetes manifests | `k8s/` | Deploy RabbitMQ, MariaDB, Selenium hub/node, API, Celery worker, Flower, and shared PVCs in a cluster. |

## Key Flow (Monday ingestion)
1. `POST /tasks` (FastAPI) creates a task record in MariaDB and enqueues the Celery `tasks.run_monday` job.
2. Celery worker consumes the job, builds `RunnerMetadata` (credentials, base URL, artifact paths) from environment variables, and calls `runner/headless_runner.run_headless_flow`.
3. `runner/flows/monday.py` logs into Monday.com, scrapes NPIs in the "Not Started" state, and posts them to `MONDAY_INGEST_API_URL` (instead of touching the DB directly).
4. Celery notifies FastAPI of status transitions (`created → in_progress → completed/failed`) via `TASK_STATUS_WEBHOOK_URL`, and the API records them in MariaDB.
5. Artifacts and structured logs are stored under `media/{task_id}/` and `app_logs/{task_id}.log`.

## Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `MONDAY_USERNAME`, `MONDAY_PASSWORD` | Credentials for Monday.com board automation | **required** |
| `MONDAY_BASE_URL` | Monday board URL | `https://pns-mgmt.monday.com/` |
| `SELENIUM_URL` | Remote Selenium hub URL | `http://selenium-hub:4444/wd/hub` |
| `MEDIA_ROOT`, `LOG_ROOT` | Directories for artifacts/logs | `media`, `app_logs` |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | MariaDB connection | defaults to `settings.py` values |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery broker/back-end (`redis://`) | ConfigMap defaults |
| `TASKS_LOG_LEVEL` | Logging level for Celery tasks | `INFO` |
| `MONDAY_INGEST_API_URL` | Webhook where Monday flow posts scraped NPIs | `http://0.0.0.0:8070/webhooks/monday` |
| `TASK_STATUS_WEBHOOK_URL` | Endpoint that receives task lifecycle updates from Celery | _(unset)_ |

## Local Development
1. Ensure MariaDB and Selenium are available (Docker compose or local installs).
2. Export required env vars and install dependencies: `pip install -r requirements.txt`.
3. Run FastAPI: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Start Celery worker: `celery -A tasks worker --loglevel=INFO`.
5. Trigger Monday automation: `curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"stage":"monday_ingest"}'`.
6. Query status: `curl http://localhost:8000/tasks/{task_id}` or `curl http://localhost:8000/tasks/{task_id}/events`.

### FastAPI ↔ Celery (Roadmap)
- FastAPI will remain the central coordination service, persisting task data in MariaDB and exposing webhook endpoints for worker callbacks.
- Celery workers now post lifecycle events to `TASK_STATUS_WEBHOOK_URL` (if provided) and never touch the database directly.
- Keep logging approachable—INFO by default, with `TASKS_LOG_LEVEL=DEBUG` surfacing detailed runner logs for troubleshooting when needed.
- The same Celery framework can power other automation pipelines (e.g., AI workloads) by reusing metadata schemas and REST hooks.

`python tasks.py` can still run the headless pipeline without creating task records—useful for quick smoke tests.

## Kubernetes Deployment
1. Build and push API/worker images (replace `ghcr.io/example/...` references in manifests).
2. Populate `k8s/configmap.yaml` and `k8s/configmap.yaml` secrets with real credentials, including Monday username/password.
3. Apply manifests: `kubectl apply -f k8s/`.
4. Monitor Celery via Flower (`kubectl port-forward service/automation-flower 5555:5555`).

## Next Steps
- Implement full Selenium automation for QuickCap and expose it via the API.
- Add Prometheus metrics, Grafana dashboards, and heartbeat monitoring.
- Expand secrets management (Vault/cloud KMS) and Kubernetes RBAC/resource tuning.
- Replace legacy constants (`constants.py`, `settings.py`) with configuration driven via env/DB.

## Commit Message
```
feat: add headless monday runner with celery tracking and k8s manifests
```
