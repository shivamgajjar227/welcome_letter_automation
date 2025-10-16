# Welcome Letter Automation – Context Snapshot

## Purpose
- Automates welcome letter preparation across external systems (Monday.com, PR Site portal, QuickCap) using Selenium-driven browser flows orchestrated by pytest.
- Captures provider NPI information from Monday boards, enriches it via PR Site lookups, and pushes the data into QuickCap while tracking progress in the `pr_site_data` table.

## Current Automation Flow (pytest)
1. `tests/test_monday.py::test_monday`
   - Logs into Monday.com through `MondayPage`, scrapes "PR Site" board rows in *Not Started* state, and stages them in MySQL (`status=0`).
2. `tests/test_pr_site.py::test_pr_site`
   - Pulls NPIs with `status=0`, extracts demographic and taxonomy data from the PR Site portal (`PRSitePage`), and updates each record (status ➜ 1, plus address/network metadata). Additional helper test `test_practice_menu_effective_date_case` targets edge cases in the PR practice view.
3. `tests/test_qc.py::test_qc`
   - Consumes `status=1` records, logs into QuickCap (`QuickcapPage`), maps company/network/category constants, and populates Quick Add workflows. The script keeps the browser session open to avoid unnecessary relogin when processing NPIs within the same company.
4. Support tests (e.g., `tests/test_monday_status.py`, `tests/test_login.py`) provide targeted checks for auxiliary flows such as monitoring board statuses or verifying login paths.

The tests are meant to run sequentially so that database state acts as the primary queue for downstream automation.

## Test & Fixture Structure
- `pytest.ini` enables HTML reporting via `pytest-html` and defines `smoke`/`regression` markers; `pytest-order` was introduced to enforce deterministic execution when chaining flows.
- `conftest.py` still owns core fixtures:
  - `driver` spins up Selenium sessions via `drivers/webdriver_manager.get_driver`; the manager now expects `SELENIUM_URL` when running against the Docker grid.
  - Functional fixtures (`monday_test`, `pr_sites_test`, `quickcap_test`) preload the relevant base URLs and return page object instances.
- Selenium page objects live under `pages/` and have expanded considerably:
  - `MondayPage` and `MondayStatusPage` split status polling from data extraction.
  - `PRSitePage` now includes retry logic, logging hooks, and helper methods for group NPI discovery, taxonomy codes, and practice menu navigation.
  - `QuickcapPage` and `QuickcapCasePage` cover credentialing workflows and organization popups with richer dropdown mappings.
- Shared lookup tables moved into top-level `constants.py` (company mapping, category map, state dropdown, templates) to keep test files lightweight.
- `core/` introduces reusable logging configuration (`loggin_utils`, `logging_module`) so page objects can emit rotating log files when the Dockerized runner mounts `/app/app_logs`.

## Database Layer
- `db/session.py` still bootstraps SQLAlchemy against the `welcome_letter` MySQL schema with optional SSH tunnelling; debug output confirms connectivity during startup.
- `models/pr_site_data.PRSiteData` gained new columns (`network`, `taxonomy_code`, `tax_id`, timestamps, address fields) used by the enriched PR Site flow; default timestamps rely on `datetime.now()`.
- `models/npi_address.NPIAddress` captures group NPI/location information discovered during PR Site scraping (not yet fully wired, but referenced in `PRSitePage`).
- CRUD helpers remain under `cruds/pr_site_data.py`, while ad-hoc inserts/updates still happen inside pytest tests; the new API skeleton in `api/pr_site_data.py` hints at future FastAPI endpoints for external enrichment services.

## Settings & Configuration
- `settings.py` aggregates numerous constants (OAuth, email, Monday API, Odoo, etc.). Many values are hard-coded defaults; `USE_DOT_ENV` can load overrides from a sibling `dpauth.env` file.
- Browser defaults (Chrome), base URLs, and credentials for portals are currently hard-coded inside tests/fixtures—consider moving to environment variables for security.

## Running Locally (bare metal)
1. Create and activate a Python 3.11+ environment (repo now pins 3.11 in the Dockerfile).
2. Install dependencies: `pip install -r requirements.txt`.
3. Ensure MariaDB is reachable using the credentials in `settings.py`, or override via env vars (`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`).
4. Launch Selenium-compatible Chrome/Chromedriver (either locally installed or via remote grid specified by `SELENIUM_URL`).
5. Trigger the new runner directly:
   - `python tasks.py` (runs Monday ingestion by default).
   - `celery -A tasks worker --loglevel=INFO` to run the worker manually.
   - `uvicorn app.main:app --reload` to expose the FastAPI endpoints locally.

Legacy pytest suites remain available (`pytest tests/test_monday.py`, etc.) for parity checks but are no longer required for the Celery pipeline.

## Docker & Kubernetes Execution
- `dockerfile` remains the base image for Selenium-enabled workloads (headless Chrome + chromedriver). Separate Dockerfiles for API/worker are recommended but pending.
- `docker-compose.yml` provisions a local Selenium Grid (`selenium-hub`, `selenium/node-chrome`) and a `test-runner` container that executes `python tasks.py` once Selenium is healthy.
- `k8s/` manifests introduce cluster-ready resources:
  - StatefulSets for RabbitMQ (`k8s/rabbitmq.yaml`) and MariaDB (`k8s/mariadb.yaml`).
  - Deployments for Selenium hub/node, FastAPI API, Celery worker, and Flower observers (`k8s/selenium.yaml`, `k8s/api-deployment.yaml`, `k8s/celery-worker.yaml`, `k8s/flower.yaml`).
  - Shared PVCs (`k8s/pvc.yaml`) and configuration/secret bundles (`k8s/configmap.yaml`).
- `check_chrome.py` still provides a quick sanity test for running Chrome headlessly with the correct flags; useful ahead of container builds.

When deploying to Kubernetes, ensure `automation-secrets` is populated with live credentials (Monday, RabbitMQ, MariaDB) and update the API/worker images (`ghcr.io/example/...`) to the built artifacts from your CI pipeline.

## Selenium Usage Notes
- `drivers/webdriver_manager.get_driver` now prefers remote execution: if `SELENIUM_URL` is defined (as in Docker compose) it connects to the grid; otherwise it falls back to local Chrome with bundled options (`--headless=new`, TLS relaxations, window maximization). Chromedriver auto-installation is available via `chromedriver-autoinstaller` when running locally.
- Explicit waits are gradually replacing `time.sleep`, but the codebase still mixes both; the new PR Site methods show retry patterns worth propagating elsewhere.
- Multi-window handling lives in `BasePage` and `QuickcapPage`; QuickCap flows open popups for organization selection, and PR Site flow navigates multiple tabs when loading group NPIs.
- Logging hooks on page objects feed rotating file handlers; ensure `/app/app_logs` exists when running in Docker.

## FastAPI & Celery Integration
- `app/main.py` exposes REST endpoints for automation task management (`POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `/tasks/{id}/events`).
- Task lifecycle data persists via `models/task_models.py` (`automation_tasks`, `automation_task_events`). Helpers in `task_tracking.py` handle creation, status transitions, and event logging.
- `tasks.py` now builds `RunnerMetadata` from environment variables, updates task state during execution, and only requires the Monday credentials to run successfully. Additional stages remain disabled until credentials are provided.
- Celery workers should point to RabbitMQ (`CELERY_BROKER_URL`) and share media/log volumes for artifact capture; Flower deployment in Kubernetes provides basic observability.

## Potential Follow-Ups
- Externalize secrets/credentials and Monday API keys to `.env` or secrets manager.
- Replace `time.sleep` with explicit waits (`WebDriverWait`) for stability.
- Expand test coverage (`tests/test_login.py` is currently a stub) and add teardown/cleanup for DB records if re-runs are needed.
- Consider driver management via `webdriver-manager` or containerized browsers for easier setup.


## Scalable Automation Platform Architecture
```mermaid
graph LR
    subgraph Frontend
        A[Next.js Portal]
    end

    subgraph Backend
        B[FastAPI Services]
        C[(MySQL DB)]
        D[(Redis/RabbitMQ Broker)]
    end

    subgraph Workers
        E[Celery Workers]
        F[[Task Runner Containers\n(Headless Selenium in Selenium Images)]]
    end

    subgraph Observability
        H[Grafana]
        J[Loki]
    end

    subgraph Local Storage
        L[(Media Artifacts Folder)]
    end

    A -->|Task CRUD, Monitoring| B
    B -->|Persist tasks, events, secrets| C
    B -->|Publish enqueue events| D
    E -->|Fetch jobs| D
    E -->|Update status/heartbeats| C
    E -->|Stream logs| J
    J -->|Dashboards| H
    E -->|Launch isolated runs| F
    F -->|Write screenshots/HTML| L
    A -->|Real-time updates| B
```

**Flow Notes**
- Next.js UI hits FastAPI for task creation, filtering, cancellation, and subscribes to WebSocket streams for live updates.
- FastAPI persists task definitions, metadata, secrets, and event history inside MariaDB and enqueues jobs onto RabbitMQ with the canonical task identifier.
- Celery workers consume RabbitMQ messages, execute headless Selenium automation inside isolated runner containers based on official Selenium browser images, update task status and heartbeats in MariaDB, and push structured logs into Loki.
- Grafana reads from Loki to provide observability dashboards and alerting; failures can surface back to the UI via WebSocket notifications.
- Artifacts such as screenshots or HTML dumps are written to a local media folder referenced in task metadata; every run captures UI screenshots for traceability and future migration to remote storage.
