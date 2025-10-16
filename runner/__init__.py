"""
Reusable headless Selenium runner utilities.

This package hosts the building blocks required to execute the Monday → PR Site
→ QuickCap automation flows without depending on pytest.  Modules are organised
so Celery tasks and command-line scripts can compose them directly.
"""

from .context import RunnerMetadata, RunnerResult, StageName, StageResult

__all__ = [
    "RunnerMetadata",
    "RunnerResult",
    "StageName",
    "StageResult",
]

