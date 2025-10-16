"""
Artifact management helpers.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from .context import ArtifactRecord, RunnerMetadata, StageName

logger = logging.getLogger(__name__)


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def stage_directory(metadata: RunnerMetadata, stage: StageName) -> Path:
    """Return the directory where artifacts for the given stage should live."""
    root = Path(metadata.media_root).expanduser().resolve()
    stage_dir = root / metadata.task_id / stage.value
    _ensure_directory(stage_dir)
    return stage_dir


def capture_screenshot(driver: WebDriver, metadata: RunnerMetadata, stage: StageName, name: str) -> ArtifactRecord:
    """Persist a PNG screenshot."""
    stage_dir = stage_directory(metadata, stage)
    filename = f"{name}.png"
    path = stage_dir / filename
    logger.info("Saving screenshot %s", path)
    driver.save_screenshot(str(path))
    return ArtifactRecord(type="screenshot", path=str(path))


def capture_dom(driver: WebDriver, metadata: RunnerMetadata, stage: StageName, name: str) -> ArtifactRecord:
    """Persist the current page source."""
    stage_dir = stage_directory(metadata, stage)
    filename = f"{name}.html"
    path = stage_dir / filename
    logger.info("Saving DOM snapshot %s", path)
    html = driver.page_source
    path.write_text(html, encoding="utf-8")
    return ArtifactRecord(type="html", path=str(path))


def capture_json(data: object, metadata: RunnerMetadata, stage: StageName, name: str) -> ArtifactRecord:
    """Persist structured JSON generated during a stage."""
    stage_dir = stage_directory(metadata, stage)
    filename = f"{name}.json"
    path = stage_dir / filename
    logger.info("Saving JSON artifact %s", path)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, sort_keys=True)
    return ArtifactRecord(type="json", path=str(path))


def ensure_media_root(media_root: Optional[str]) -> None:
    """Ensure the root media directory exists to avoid runtime issues."""
    if not media_root:
        return
    root = Path(media_root).expanduser()
    _ensure_directory(root)
    logger.debug("Media root ensured at %s", root.resolve())

