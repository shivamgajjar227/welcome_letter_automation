"""Helpers for posting runner results to external webhooks."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from requests import RequestException

from .auth import request_with_auth
from .context import RunnerMetadata, StageName
from copy import deepcopy

logger = logging.getLogger(__name__)


def get_stage_webhook(metadata: RunnerMetadata, stage: StageName) -> Optional[str]:
    config = metadata.stage_config.get(stage)
    if not config:
        return None
    return config.extra.get("webhook_url")  # type: ignore[arg-type]


def post_webhook(metadata: RunnerMetadata, stage: StageName, payload: Mapping[str, Any]) -> bool:
    url = get_stage_webhook(metadata, stage)
    if not url:
        logger.debug("No webhook configured for stage %s", stage.value)
        return False
    try:
        response = request_with_auth("POST", url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Webhook posted", extra={"stage": stage.value, "url": url, "status": response.status_code})
        return True
    except RequestException as exc:
        logger.warning("Webhook post failed", extra={"stage": stage.value, "url": url, "error": str(exc)})
        return False

def post_create_task_units(payload):
    url = "http://0.0.0.0:10022/api/task_units/create"
    if not url:
        logger.debug("No webhook configured for task unit")
        return False
    try:
        response = request_with_auth("POST", url, json=payload, timeout=30)
        logger.debug("Webhook posted", extra={"url": url, "status": response.status_code})
        """
        Convert to task unit dict
        key: identifier(like npi)
        value: object of response
        """
        response = response.json()
        temp_task_unit_dict = {}
        for resp_obj in response["created_units"]:
            temp_task_unit_dict[resp_obj["identifier"]] = resp_obj
        return deepcopy(temp_task_unit_dict)
    except RequestException as exc:
        logger.warning("Webhook post failed", extra={"url": url, "status": response.status_code,"error": str(exc)})
        return False

def post_update_state_task_units(payload):
    try:
        url = "http://0.0.0.0:10022/api/task_units/state_update"
        response = request_with_auth("POST", url, json=payload, timeout=30)
        logger.debug("Webhook posted", extra={"url": url, "status": response.status_code})
        return response.json()
    except RequestException as exc:
        logger.warning("Webhook post failed", extra={"url": url, "status": response.status_code})
        return False


def get_stage_input_url(metadata: RunnerMetadata, stage: StageName) -> Optional[str]:
    config = metadata.stage_config.get(stage)
    if not config:
        return None
    return config.extra.get('input_url')  # type: ignore[arg-type]


def fetch_stage_payload(metadata: RunnerMetadata, stage: StageName) -> Optional[Mapping[str, Any]]:
    url = get_stage_input_url(metadata, stage)
    if not url:
        logger.debug('No input URL configured for stage %s', stage.value)
        return None
    try:
        response = request_with_auth("GET", url, timeout=30)
        response.raise_for_status()
        return response.json()
    except RequestException as exc:
        logger.warning('Failed to fetch input payload', extra={'stage': stage.value, 'url': url, 'error': str(exc)})
        return None
