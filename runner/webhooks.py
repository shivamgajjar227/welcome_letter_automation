"""Helpers for posting runner results to external webhooks."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

import requests
from requests import RequestException

from .context import RunnerMetadata, StageName

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
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Webhook posted", extra={"stage": stage.value, "url": url, "status": response.status_code})
        return True
    except RequestException as exc:
        logger.warning("Webhook post failed", extra={"stage": stage.value, "url": url, "error": str(exc)})
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
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except RequestException as exc:
        logger.warning('Failed to fetch input payload', extra={'stage': stage.value, 'url': url, 'error': str(exc)})
        return None
