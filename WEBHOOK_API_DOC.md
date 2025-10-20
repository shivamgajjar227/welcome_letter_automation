# Webhook API Reference

This document describes the REST interfaces that a FastAPI server should expose to support the Celery-based automation workflows. There are two inbound webhook categories:

1. **Monday ingestion webhook** – the headless runner posts NPI records scraped from Monday.com.
2. **Task status webhook** – Celery workers notify the API of lifecycle transitions (`in_progress`, `completed`, `failed`, etc.).

## 1. Monday Ingestion Webhook

- **Endpoint**: `POST /webhooks/monday`
- **Purpose**: Receive the list of NPIs scraped from Monday’s "PR Site" board so the API can validate and persist them (e.g., into `pr_site_data`).
- **Headers**: `Content-Type: application/json`
- **Request Body**:

```json
{
  "task_id": "<uuid>",
  "stage": "monday_ingest",
  "records": [
    {
      "npi_number": "1508446295",
      "effective_date": "Oct 1",
      "health_plan": "Aetna",
      "lines_of_business": "Aetna"
    },
    {
      "npi_number": "1912217936",
      "effective_date": "Oct 1",
      "health_plan": "Doctors",
      "lines_of_business": "Doctors"
    }
    // ...additional entries
  ]
}
```

- **Response**: `200 OK`

```json
{"status": "ok"}
```

- **Notes**:
  - `task_id` maps to the Celery task ID, allowing you to correlate ingestion results with task status updates.
  - `stage` currently uses `"monday_ingest"`; future flows (PR Site, QuickCap) should send their own identifiers.
  - Validate payloads before persisting to the database (e.g., check for duplicates, enforce data integrity, or enrich fields).

## 2. Task Status Webhook

- **Endpoint**: `POST /webhooks/task-status`
- **Purpose**: Receive lifecycle updates from Celery workers so FastAPI can record task state transitions in MariaDB (or another datastore).
- **Headers**: `Content-Type: application/json`
- **Request Body**:

```json
{
  "task_id": "d82c080a-3d1d-4c7b-92dd-479796742660",
  "status": "completed",
  "stage": "monday_ingest",
  "result": {
    "data": {
      "records": [
        {
          "npi_number": "1508446295",
          "effective_date": "Oct 1",
          "health_plan": "Aetna",
          "lines_of_business": "Aetna"
        }
        // ...
      ]
    },
    "artifacts": [
      {
        "type": "screenshot",
        "path": "/media/<task_id>/monday_ingest/after_login.png"
      },
      {
        "type": "html",
        "path": "/media/<task_id>/monday_ingest/npis_table.html"
      }
    ]
  },
  "message": null
}
```

- **Response**: `200 OK`

```json
{"status": "ok"}
```

- **Status Values**:
  - `in_progress` – worker has begun executing the stage.
  - `completed` – stage finished successfully; `result` contains data/artifacts.
  - `failed` – stage encountered an error; `message` describes the failure.

- **Notes**:
  - The webhook is optional; if `TASK_STATUS_WEBHOOK_URL` is unset, the worker logs the status locally.
  - FastAPI should store or update task records based on `task_id`, leveraging `result` details (artifacts, data) for downstream processing.
  - For multi-stage pipelines, each stage should send its own update, enabling granular progress tracking.

## Additional Considerations

- **Security**: Protect webhook endpoints (e.g., via shared secret headers, IP allowlists, or OAuth) before exposing them publicly.
- **Idempotency**: Implement idempotent logic so re-delivered webhooks do not create duplicate records.
- **Validation**: Use Pydantic models or similar validation to ensure payloads conform to expected schema.
- **Observability**: Log incoming webhook payloads (with caution for sensitive data) and expose metrics (count, failures) for monitoring.

By implementing these endpoints, the FastAPI service can fully orchestrate the Celery-driven automation pipeline without workers accessing the database directly.
