# Headless Selenium Runner PoC – Developer Guide

## Objective
Stand up a reproducible proof-of-concept that executes the existing Selenium automation flows in a Linux server environment **without a virtual display**. This PoC focuses on building a reusable Python function that encapsulates browser setup, execution, artifact capture, and cleanup in headless mode. The function will be the foundation for the Celery task implementation planned in the full platform architecture.

## Scope
- Run the automation inside a Docker container derived from the official `selenium/standalone-chrome` image.
- Use Chrome’s native headless mode (`--headless=new`) with all required stability flags.
- Capture screenshots and HTML dumps for each major step and persist them to the local media folder (same location that will later be exposed through the API).
- Structure the code so it can be imported today as a normal Python callable and later wrapped with `@celery_app.task` without refactoring.
- Do **not** integrate RabbitMQ/Celery for this phase; focus purely on validating headless Selenium execution, artifact capture, and data access.

## Deliverables
1. New module (proposal: `runner/headless_runner.py`) exporting a single entry function `run_headless_flow(metadata: dict) -> RunResult`.
2. Supporting utilities for driver setup, artifact handling, and logging.
3. Docker command / script to launch the `selenium/standalone-chrome` container and run the PoC.
4. Documentation (this file) describing design decisions, environment setup, execution steps, and future Celery integration points.

## Tech Stack Choices
- **Python**: reuse the project’s existing version (3.12) for orchestration code.
- **Browser Image**: `selenium/standalone-chrome:latest` (bundled Chrome + ChromeDriver + Supervisor).
- **Automation Libraries**: the current Selenium bindings already used in the repo.
- **Logging**: Python `logging` module configured for structured logs (JSON or key-value) so eventual Loki integration is straightforward.
- **Artifacts**: local folder (default `media/`) mounted into the container.

## Proposed Directory Layout
```
welcome_letter_automation/
├── runner/
│   ├── __init__.py
│   ├── headless_runner.py       # new PoC entry point
│   ├── browser.py               # driver factory & options helpers
│   ├── artifacts.py             # artifact path helpers
│   └── context.py               # dataclasses for metadata & results
├── tests/
│   └── test_headless_runner.py  # optional smoke test hitting the PoC
└── POC_HEADLESS_RUNNER.md
```

## Function Contract
```python
from runner.context import RunnerMetadata, RunnerResult

def run_headless_flow(metadata: RunnerMetadata) -> RunnerResult:
    """Executes Monday → PR Site → QuickCap automation in headless Chrome.

    Steps:
    1. Prepare working directories for logs/artifacts.
    2. Build Selenium options for headless Chrome.
    3. Execute each sub-flow (monday, pr_site, quickcap), capturing
       screenshots/HTML after key transitions.
    4. Persist results and return summary for logging or future DB persistence.
    """
```

- `RunnerMetadata` holds inputs such as URLs, credentials references, feature toggles (`run_monday=True`, etc.), and artifact base path.
- `RunnerResult` encapsulates elapsed time, success flag, captured artifact paths, and any structured data extracted (e.g., NPI entries).

## Sub-flow Organisation
Break the existing `tests/quickcap_suite.py` logic into composable functions:
- `monday.collect_npis(driver, metadata) -> list[NPISourceRecord]`
- `pr_site.enrich(driver, metadata, npis) -> list[EnrichedRecord]`
- `quickcap.submit(driver, metadata, records) -> SubmissionSummary`

These functions can live under `runner/flows/` or reuse existing page objects but should explicitly avoid pytest fixtures. Each sub-flow should call `save_artifact(driver, stage_name)` to create `PNG` screenshots and optional `HTML` dumps.

## Artifact Handling
- Use `artifacts.ensure_stage_folder(task_id, stage)` to create `media/{task_id}/{stage}/`.
- `artifacts.capture_screenshot(driver, path)` for PNGs (`driver.save_screenshot`).
- `artifacts.capture_dom(driver, path)` to dump HTML (`driver.page_source`).
- Return a dictionary `{stage: {"screenshot": path, "html": path}}` from the runner for downstream consumers.

## Logging Strategy
Configure a module-level logger in `headless_runner.py`:
```python
logger = logging.getLogger("runner.headless")
logger.setLevel(logging.INFO)
```
- Emit structured entries (`logger.info("stage_start", extra={"stage": stage})`).
- On exceptions, capture screenshot/HTML, log with stack trace, and propagate an error flag through `RunnerResult`.

## Docker Execution Plan
1. Build a lightweight helper image (optional) or use the selenium image directly.
2. Example command:
```bash
docker run --rm \
  -e PYTHONPATH=/workspace \
  -v $(pwd):/workspace \
  -v $(pwd)/media:/workspace/media \
  selenium/standalone-chrome:latest \
  bash -lc "pip install -r requirements.txt && python scripts/run_headless_poc.py"
```
3. `scripts/run_headless_poc.py` will import `runner.headless_runner` and call `run_headless_flow` with sample metadata sourced from env variables.

### Required Environment Variables
- `MONDAY_USER`, `MONDAY_PASS`
- `PR_SITE_USER`, `PR_SITE_PASS`
- `QUICKCAP_USER`, `QUICKCAP_PASS`
- `MEDIA_ROOT` (default `/workspace/media`)
- `TASK_ID` for artifact namespacing (default timestamp).

## Step-by-Step Execution Outline
1. **Prepare environment**
   - Ensure `requirements.txt` dependencies are installed inside the container.
   - Create `media/` directory and ensure it is writable.
2. **Invoke runner**
   - Construct `RunnerMetadata` from env vars or JSON file.
   - Call `run_headless_flow(metadata)`.
3. **Within runner**
   - Initialize logging and unique `task_id`.
   - Acquire WebDriver via `browser.headless_chrome()`.
   - For each enabled sub-flow:
     - Log stage start.
     - Execute the flow function, capturing artifacts at meaningful checkpoints.
     - Persist intermediate data to DB (optional for PoC) or in-memory for the returned result.
   - Close the WebDriver cleanly.
4. **Output handling**
   - Print JSON summary of `RunnerResult` to stdout.
   - Verify that screenshots/HTML files exist under `media/{task_id}/`.

## Error Handling & Retry
- Wrap each sub-flow in try/except.
- On failure: capture final screenshot + DOM, log the exception, set `result.status = "failed"`, and re-raise or return the failure state depending on how the PoC script should behave.
- Consider transient failure classification for future automatic retries (will be relevant once Celery is introduced).

## Verification Checklist
- [ ] Headless Chrome launches successfully in the container without Xvfb.
- [ ] Automation actions execute against target environments in headless mode.
- [ ] Screenshots and HTML dumps are captured per stage.
- [ ] Runner returns structured result data.
- [ ] Logs show stage transitions and errors clearly.
- [ ] Container exits cleanly, leaving artifacts accessible on the host.

## Preparing for Celery Integration
- Keep the `run_headless_flow` signature stable; a future Celery task can simply call it and relay the `RunnerResult` to MariaDB.
- Ensure logging and artifact paths can be linked to a `task_id` (Celery task ID later).
- Factor out configuration parsing so Celery workers can inject metadata from DB.
- Document any external prerequisites (VPN access, network allowlists) that Celery workers must satisfy.

## Hand-off Notes for Collaborators
- This document plus the scaffolded modules are sufficient for another developer to implement the PoC without dealing with the broader architecture.
- Prioritize finishing the headless runner before touching API/Celery code.
- Use Git branches dedicated to the PoC to avoid interfering with current pytest scripts.
- After successful PoC runs, schedule a review to promote the runner into the Celery worker stack and update `PROJECT_CONTEXT.md` with empirical findings (latency, failure modes, etc.).

