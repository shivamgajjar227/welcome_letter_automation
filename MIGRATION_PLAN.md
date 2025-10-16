# Automation Platform Migration Plan

Goal: Transition the welcome-letter automation project from pytest-driven test scripts to a reusable headless Selenium runner orchestrated by Celery tasks and exposed through a FastAPI service, while maintaining clear separation of concerns and deployable Docker targets.

## Current Status (Updated)
- ✅ Phase 0 scaffolding complete: runner package now includes context models, browser factory, artifact helpers, logging setup, and a production-ready Monday ingestion flow (PR Site/QuickCap scaffolds remain to be expanded).
- ✅ Celery tasks now persist lifecycle data in MariaDB (`automation_tasks`, `automation_task_events`) and the FastAPI API exposes task creation/query endpoints for Monday-only runs.
- ⏳ Pending: add full Selenium automation for QuickCap, expose PR Site once validated, and extend observability/metrics before multi-stage rollout.

## Phase 0 – Stabilize Headless Runner Core
1. Implement `runner/` package:
   - `runner/context.py`: dataclasses for metadata (URLs, credentials, toggles) and run results.
   - `runner/browser.py`: factory for headless Chrome `webdriver.Remote`, supporting `SELENIUM_URL` and local fallback.
   - `runner/artifacts.py`: helpers for screenshot/HTML capture into `media/{task_id}/stage/`.
   - `runner/logging.py`: configure structured logging (JSON) with rotation under `app_logs/`.
   - `runner/flows/{monday, pr_site, quickcap}.py`: pure functions encapsulating existing page-object interactions; remove pytest asserts and fixtures.
   - `runner/headless_runner.py`: orchestrates the three flows, collects artifacts, handles retries, returns `RunnerResult`.
2. Update page objects to accept hooks for artifact capture instead of printing; ensure no pytest dependencies remain.
3. Add unit/integration tests that run the runner in dry-run mode (mock browser) to ensure serialization of metadata and artifacts.

## Phase 1 – Replace pytest Entry Points
1. Refactor `tasks.py` to call `runner/headless_runner.run_headless_flow()` instead of `pytest.main`.
2. Provide CLI (`python scripts/run_pipeline.py`) for manual runs using the same runner function.
3. Remove direct pytest dependencies from Celery tasks; keep pytest only for automated testing.

## Phase 2 – Celery & RabbitMQ Integration
1. Configure Celery app:
   - Use RabbitMQ as broker (`CELERY_BROKER_URL=amqp://`); Redis optional as result backend.
   - Define task state updates via helper module (write to MariaDB `tasks` table, emit heartbeats).
2. Implement Celery tasks:
   - `tasks.run_monday`, `tasks.run_pr_site`, `tasks.run_quickcap` call `run_headless_flow` with stage filters.
   - `tasks.run_pipeline` chains/ groups tasks using Celery primitives; store combined results.
3. Add Flower monitoring service in docker-compose.
4. Ensure tasks capture artifacts/log paths and persist them to DB.

## Phase 3 – FastAPI Service Layer
1. Create `app/` package:
   - `app/main.py`: FastAPI init with routers, websocket manager, Prometheus metrics endpoint.
   - `app/config.py`: Pydantic settings for DB, RabbitMQ, media paths.
   - `app/db.py`: SQLAlchemy session factory, Alembic migrations.
   - `app/models.py` / `app/schemas.py`: ORM models for `task_queues`, `task_types`, `tasks`, `task_events`, `task_logs`.
   - `app/routers/tasks.py`: CRUD endpoints (`POST /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/cancel`, etc.).
   - `app/services/task_service.py`: encapsulates DB writes and Celery invocation.
   - `app/websocket.py`: push task updates/logs to connected clients.
2. Integrate secrets workflow (for now, CRUD in MariaDB table with encryption-at-rest or environment-based key).
3. Add dependency-injected logger and artifact resolver for API.

## Phase 4 – Docker & Deployment Targets
1. Create separate Dockerfiles:
   - `docker/Dockerfile.api`: FastAPI app (uvicorn) with dependencies, no browser.
   - `docker/Dockerfile.worker`: Celery worker image with runner + headless Chrome (extend current Dockerfile).
2. Update docker-compose:
   - Services: `api`, `celery-worker`, `celery-beat` (optional), `flower`, `rabbitmq`, `mariadb`, `selenium-hub`, `chrome-node`.
   - Share volumes for `/app/media` and `/app/app_logs`.
   - Define healthchecks for RabbitMQ, Selenium, MariaDB.
3. Provide `.env` templates for local development; ensure secrets pulled from env.
4. Kubernetes rollout:
   - `k8s/rabbitmq.yaml`, `k8s/mariadb.yaml`, `k8s/selenium.yaml` for infrastructure services.
   - `k8s/api-deployment.yaml`, `k8s/celery-worker.yaml`, `k8s/flower.yaml`, and shared PVC/config manifests.

## Phase 5 – Observability & Logging
1. Standardize logging: JSON format, include `task_id`, `stage`, `event` fields.
2. Configure Loki + Promtail in Docker for log ingestion; Grafana dashboards for key metrics (task success rate, duration, queue depth).
3. Expose Prometheus metrics from FastAPI and Celery (via `prometheus_client`).
4. Implement heartbeat watchdog to mark stale tasks as `failed`.

## Phase 6 – Frontend Integration Readiness
1. Document REST/WebSocket contracts for Next.js portal.
2. Provide sample payloads and metadata JSON schema (steps, secrets, capabilities, etc.).
3. Ensure artifact URLs are exposed via signed endpoints.

## Backlog / Future Refactors
- Replace Selenium with Playwright for improved headless stability (evaluate after MVP).
- Move secrets from MariaDB to Vault or cloud secret manager.
- Implement retry policies with exponential backoff per task type.
- Add automated cleanup of old media/log artifacts.
- Expand unit tests to mock external systems (Monday, PR Site, QuickCap).
- Replace constants.py dictionaries with DB-driven configuration tables.
- Investigate using Kubernetes Jobs instead of long-running Celery workers for better isolation.
- Harden Kubernetes manifests (RBAC, resource requests/limits, secret management) and integrate with cluster-level monitoring/alerts.

## Execution Notes
- Tackle phases sequentially but commit in small, reviewable increments.
- Keep pytest tests operational until Phase 1 finishes; run both pipelines in CI for parity checks.
- Update `PROJECT_CONTEXT.md` and architecture diagrams after each major milestone to keep documentation aligned.
