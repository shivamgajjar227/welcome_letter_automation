"""
Logging configuration tailored for runner executions.
"""

from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path
from typing import Optional

from .context import RunnerMetadata


DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _ensure_log_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


def configure_logging(metadata: RunnerMetadata, level: str = "INFO", *, structured: bool = True) -> None:
    """
    Configure the logging subsystem for a runner invocation.

    When `structured` is True, logs are formatted as JSON for easy ingestion
    into systems such as Loki.  Otherwise a plaintext formatter is used.
    """
    log_dir = Path(metadata.log_root).expanduser()
    _ensure_log_dir(log_dir)

    log_path = log_dir / f"{metadata.task_id}.log"

    if structured:
        formatter = {
            "format": "%(message)s",
            "class": "logging.Formatter",
        }
    else:
        formatter = {
            "format": DEFAULT_FORMAT,
            "class": "logging.Formatter",
        }

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": formatter,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "level": level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_path),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "formatter": "structured",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": level,
        },
    }

    logging.config.dictConfig(config)


def structured_log(logger: logging.Logger, event: str, **fields: object) -> None:
    """
    Emit a JSON-formatted log line via *logger* with mandatory `event` field.
    """
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, default=str))

