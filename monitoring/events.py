"""
Asynchronous helpers for posting automation telemetry to backend webhooks.
"""

from __future__ import annotations

import base64
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence
from uuid import uuid4

from requests import RequestException

from config import get_settings
from runner.auth import request_with_auth
from runner.context import ArtifactRecord, StageName

logger = logging.getLogger(__name__)

_settings = get_settings()
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="telemetry")


def _as_stage_value(stage: StageName | str) -> str:
    return stage.value if isinstance(stage, StageName) else str(stage)


def _submit(url: Optional[str], payload: Mapping[str, Any]) -> None:
    if not url:
        logger.debug("Skipping telemetry post (url missing): %s", payload.get("event") or payload.get("stage"))
        return

    def _post() -> None:
        try:
            response = request_with_auth("POST", url, json=payload, timeout=10)
            response.raise_for_status()
        except RequestException as exc:
            logger.warning("Failed to post telemetry to %s: %s", url, exc, exc_info=False)

    _executor.submit(_post)


def emit_stage_event(
    *,
    task_id: str,
    stage: StageName | str,
    event: str,
    status: Optional[str] = None,
    celery_id: Optional[str] = None,
    stage_run_id: Optional[str] = None,
    summary: Optional[Mapping[str, Any]] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    duration_ms: Optional[int] = None,
    message: Optional[str] = None,
    artifacts: Optional[Sequence[Mapping[str, Any]]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    payload: MutableMapping[str, Any] = {
        "task_id": task_id,
        "stage": _as_stage_value(stage),
        "event": event,
    }
    if stage_run_id:
        payload["stage_run_id"] = stage_run_id
    if celery_id:
        payload["celery_id"] = celery_id
    if status:
        payload["status"] = status
    if started_at:
        payload["started_at"] = started_at
    if finished_at:
        payload["finished_at"] = finished_at
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if summary:
        payload["summary"] = dict(summary)
    if message:
        payload["message"] = message
    if artifacts:
        payload["artifacts"] = list(artifacts)
    if metadata:
        payload["metadata"] = dict(metadata)

    _submit(_settings.stage_events_webhook_url, payload)


def emit_npi_event(
    *,
    task_id: str,
    stage: StageName | str,
    npi: str,
    status: str,
    attempt: int = 1,
    stage_run_id: Optional[str] = None,
    input_snapshot: Optional[Mapping[str, Any]] = None,
    output_snapshot: Optional[Mapping[str, Any]] = None,
    diff: Optional[Mapping[str, Any]] = None,
    artifacts: Optional[Sequence[Mapping[str, Any]]] = None,
    message: Optional[str] = None,
) -> None:
    payload: MutableMapping[str, Any] = {
        "task_id": task_id,
        "stage": _as_stage_value(stage),
        "npi": npi,
        "status": status,
        "attempt": attempt,
    }
    if stage_run_id:
        payload["stage_run_id"] = stage_run_id
    if input_snapshot:
        payload["input_snapshot"] = dict(input_snapshot)
    if output_snapshot:
        payload["output_snapshot"] = dict(output_snapshot)
    if diff:
        payload["diff"] = dict(diff)
    if artifacts:
        payload["artifacts"] = list(artifacts)
    if message:
        payload["message"] = message

    _submit(_settings.npi_events_webhook_url, payload)


def _artifact_storage_url(artifact_path: str, *, task_id: str, stage: StageName | str) -> Optional[str]:
    base_url = _settings.artifact_base_url
    if not base_url:
        return None
    filename = os.path.basename(artifact_path)
    return "/".join(
        part.strip("/")
        for part in (base_url, task_id, _as_stage_value(stage), filename)
        if part
    )


def upload_artifacts(
    *,
    task_id: str,
    stage: StageName | str,
    artifacts: Iterable[ArtifactRecord],
) -> List[Mapping[str, Any]]:
    artifact_list = list(artifacts)
    if not artifact_list:
        return []

    payload_artifacts: List[Mapping[str, Any]] = []
    references: List[Mapping[str, Any]] = []

    for record in artifact_list:
        artifact_id = uuid4().hex
        path_obj = Path(record.path)
        content_b64: Optional[str] = None
        try:
            content_b64 = base64.b64encode(path_obj.read_bytes()).decode("ascii")
        except OSError as exc:
            logger.warning("Failed to read artifact %s: %s", path_obj, exc, exc_info=False)

        artifact_payload: MutableMapping[str, Any] = {
            "artifact_id": artifact_id,
            "type": record.type,
            "label": path_obj.name,
            "path": str(path_obj),
        }
        if record.description:
            artifact_payload["description"] = record.description
        if content_b64:
            artifact_payload["content_base64"] = content_b64
        storage_url = _artifact_storage_url(str(path_obj), task_id=task_id, stage=stage)
        if storage_url:
            artifact_payload["storage_url"] = storage_url

        payload_artifacts.append(artifact_payload)
        references.append(
            {
                "artifact_id": artifact_id,
                "type": record.type,
                "label": path_obj.name,
                "storage_url": storage_url,
            }
        )

    payload = {
        "task_id": task_id,
        "stage": _as_stage_value(stage),
        "artifacts": payload_artifacts,
    }
    _submit(_settings.artifact_events_webhook_url, payload)
    return references


def emit_pipeline_event(
    *,
    task_id: str,
    event: str,
    celery_id: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    payload: MutableMapping[str, Any] = {
        "task_id": task_id,
        "event": event,
    }
    if celery_id:
        payload["celery_id"] = celery_id
    if status:
        payload["status"] = status
    if metadata:
        payload["metadata"] = dict(metadata)

    _submit(_settings.pipeline_events_webhook_url, payload)
