"""
Top-level orchestration for the headless Selenium automation pipeline.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict

from selenium.webdriver.remote.webdriver import WebDriver

from . import artifacts
from .browser import browser_session
from .context import RunnerMetadata, RunnerResult, StageConfig, StageName, StageResult
from .flows import monday, monday_status, pr_site, quickcap
from .logging import configure_logging, structured_log

logger = logging.getLogger(__name__)

StageCallable = Callable[[WebDriver, RunnerMetadata], StageResult]


STAGE_IMPLEMENTATIONS: Dict[StageName, StageCallable] = {
    StageName.MONDAY: monday.run,
    StageName.MONDAY_STATUS: monday_status.run,
    StageName.PR_SITE: pr_site.run,
    StageName.QUICKCAP: quickcap.run,
}


def _stage_config(metadata: RunnerMetadata, stage: StageName) -> StageConfig:
    config = metadata.stage_config.get(stage)
    if config:
        return config
    return StageConfig()


def run_headless_flow(metadata: RunnerMetadata) -> RunnerResult:
    """
    Execute the automation pipeline using the supplied metadata.

    Stages execute in the order defined by :class:`StageName`.  Execution stops
    at the first failure and returns the partial `RunnerResult`.
    """
    artifacts.ensure_media_root(metadata.media_root)
    configure_logging(metadata)

    structured_log(logger, "runner_start", task_id=metadata.task_id)

    result = RunnerResult(task_id=metadata.task_id, metadata=metadata)

    with browser_session(metadata, headless=metadata.headless) as driver:
        for stage in StageName:
            impl = STAGE_IMPLEMENTATIONS.get(stage)
            if impl is None:
                structured_log(logger, "stage_skip_unimplemented", task_id=metadata.task_id, stage=stage.value)
                continue

            config = _stage_config(metadata, stage)
            if not config.enabled:
                structured_log(logger, "stage_skip_disabled", task_id=metadata.task_id, stage=stage.value)
                continue

            source_stage_value = config.extra.get("payload_from")
            if source_stage_value:
                try:
                    source_stage = StageName(source_stage_value)
                    source_result = result.stages.get(source_stage)
                    if source_result:
                        payload_key = config.extra.get("payload_key", "records")
                        records = source_result.data.get(payload_key)
                        if records is not None:
                            metadata.request_payload = {"records": records}
                except ValueError:
                    logger.warning("Unknown payload_from stage %s", source_stage_value)

            structured_log(logger, "stage_execute", task_id=metadata.task_id, stage=stage.value)
            stage_result = impl(driver, metadata)
            result.add_stage(stage_result)

            if not stage_result.success:
                structured_log(logger, "stage_halt_on_failure", task_id=metadata.task_id, stage=stage.value)
                break

            # reset payload to avoid leaking data when next stage pulls via REST
            metadata.request_payload = {}

    result.mark_finished()
    structured_log(logger, "runner_finished", task_id=metadata.task_id, success=result.success)
    return result
