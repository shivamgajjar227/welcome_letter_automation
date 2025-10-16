"""
Data models that capture runner inputs and outputs.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, MutableMapping, Optional


class StageName(str, Enum):
    """Enumeration of the automation stages."""

    MONDAY = "monday_ingest"
    PR_SITE = "pr_site_enrichment"
    QUICKCAP = "quickcap_submission"


def _default_task_id() -> str:
    return uuid.uuid4().hex


@dataclass(slots=True)
class StageConfig:
    """Configuration for an individual runner stage."""

    enabled: bool = True
    extra: MutableMapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CredentialRef:
    """Represents a logical credential reference (username/password pair)."""

    username: str
    password: str


@dataclass(slots=True)
class RunnerMetadata:
    """
    Aggregated metadata required to execute a headless run.

    Attributes:
        task_id: Identifier used for logs/artifacts; defaults to a UUID.
        selenium_url: Remote WebDriver endpoint.  If None, a local driver will be used.
        media_root: Root directory for artifacts (screenshots, HTML dumps).
        log_root: Root directory for structured log files.
        base_urls: Mapping of stage names to URL strings.
        credentials: Mapping of logical keys to credential references.
        stage_config: Per-stage toggles or specific metadata.
        request_payload: Original task payload (stored for auditing or replays).
    """

    task_id: str = field(default_factory=_default_task_id)
    selenium_url: Optional[str] = None
    media_root: str = "media"
    log_root: str = "app_logs"
    base_urls: Mapping[str, str] = field(default_factory=dict)
    credentials: Mapping[str, CredentialRef] = field(default_factory=dict)
    stage_config: Mapping[StageName, StageConfig] = field(default_factory=dict)
    request_payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactRecord:
    """Describes a single artifact produced during a stage."""

    type: str  # e.g. "screenshot", "html"
    path: str
    description: Optional[str] = None


@dataclass(slots=True)
class StageResult:
    """Result of a single automation stage."""

    stage: StageName
    started_at: _dt.datetime = field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
    finished_at: Optional[_dt.datetime] = None
    success: bool = False
    error: Optional[str] = None
    data: MutableMapping[str, Any] = field(default_factory=dict)
    artifacts: List[ArtifactRecord] = field(default_factory=list)

    def mark_finished(self, success: bool, error: Optional[str] = None) -> None:
        self.success = success
        self.error = error
        self.finished_at = _dt.datetime.now(_dt.timezone.utc)


@dataclass(slots=True)
class RunnerResult:
    """Aggregated result for the full run."""

    task_id: str
    started_at: _dt.datetime = field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
    finished_at: Optional[_dt.datetime] = None
    stages: MutableMapping[StageName, StageResult] = field(default_factory=dict)
    metadata: RunnerMetadata = field(default_factory=RunnerMetadata)

    def add_stage(self, stage_result: StageResult) -> None:
        self.stages[stage_result.stage] = stage_result

    def mark_finished(self) -> None:
        self.finished_at = _dt.datetime.now(_dt.timezone.utc)

    @property
    def success(self) -> bool:
        if not self.stages:
            return False
        return all(stage.success for stage in self.stages.values())

