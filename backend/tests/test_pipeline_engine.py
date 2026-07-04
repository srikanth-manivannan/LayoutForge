from pathlib import Path

import pytest

from app.pipeline.context import PipelineContext
from app.pipeline.engine import PipelineEngine, PipelineStageError, StageProgress
from app.pipeline.stages.base import Stage


class RecordingStage(Stage):
    def __init__(self, label: str, calls: list[str]) -> None:
        self._label = label
        self._calls = calls

    @property
    def name(self) -> str:
        return self._label

    def run(self, context: PipelineContext) -> None:
        self._calls.append(self._label)


class FailingStage(Stage):
    @property
    def name(self) -> str:
        return "failing"

    def run(self, context: PipelineContext) -> None:
        raise ValueError("boom")


def make_context() -> PipelineContext:
    return PipelineContext(
        job_id="job-1",
        project_id="project-1",
        source_pdf_path=Path("source.pdf"),
        output_dir=Path("out"),
    )


def test_engine_runs_stages_in_order_and_reports_progress() -> None:
    calls: list[str] = []
    progress_updates: list[StageProgress] = []

    engine = PipelineEngine(
        stages=[RecordingStage("a", calls), RecordingStage("b", calls), RecordingStage("c", calls)],
        on_progress=progress_updates.append,
    )

    engine.run(make_context())

    assert calls == ["a", "b", "c"]
    assert [p.progress for p in progress_updates] == [33, 67, 100]
    assert progress_updates[-1].stage == "c"


def test_engine_wraps_stage_failure_with_stage_name() -> None:
    engine = PipelineEngine(stages=[FailingStage()])

    with pytest.raises(PipelineStageError) as exc_info:
        engine.run(make_context())

    assert exc_info.value.stage_name == "failing"
