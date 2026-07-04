import logging
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass, field

from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import Stage

pipeline_logger = logging.getLogger("layoutforge.pipeline")
performance_logger = logging.getLogger("layoutforge.performance")


@dataclass
class StageProgress:
    stage: str
    stage_index: int
    total_stages: int
    progress: int  # 0-100, written directly, never recomputed by callers
    duration_seconds: float


@dataclass
class StageMetric:
    """Per-stage timing + peak memory (M1.7 engine stabilization) — the raw
    data behind performance regression tests and the conversion report."""

    stage: str
    duration_seconds: float
    peak_memory_mb: float


OnProgress = Callable[[StageProgress], None]


class PipelineStageError(RuntimeError):
    """Raised when a stage fails; carries the stage name that failed."""

    def __init__(self, stage_name: str, original: Exception) -> None:
        super().__init__(f"Stage '{stage_name}' failed: {original}")
        self.stage_name = stage_name
        self.original = original


class PipelineEngine:
    """Runs an ordered list of Stages against a PipelineContext.

    The engine is the only thing that knows the execution backend. Today
    stages run synchronously in a FastAPI BackgroundTask; swapping in
    Celery/RQ/Kubernetes Jobs later means changing how `run` is invoked,
    not the Stage implementations themselves.
    """

    def __init__(self, stages: list[Stage], on_progress: OnProgress | None = None) -> None:
        self._stages = stages
        self._on_progress = on_progress
        # Populated as stages run; consumed by the conversion report.
        self.metrics: list[StageMetric] = []

    def run(self, context: PipelineContext) -> None:
        total = len(self._stages)
        self.metrics = []
        tracing = not tracemalloc.is_tracing()
        if tracing:
            tracemalloc.start()
        try:
            for index, stage in enumerate(self._stages, start=1):
                pipeline_logger.info("job=%s stage=%s starting", context.job_id, stage.name)
                tracemalloc.reset_peak()
                started = time.perf_counter()
                try:
                    stage.run(context)
                except Exception as exc:  # noqa: BLE001 - re-raised as a typed pipeline error
                    pipeline_logger.error("job=%s stage=%s failed: %s", context.job_id, stage.name, exc)
                    raise PipelineStageError(stage.name, exc) from exc
                duration = time.perf_counter() - started
                _current, peak = tracemalloc.get_traced_memory()
                peak_mb = peak / (1024 * 1024)
                self.metrics.append(StageMetric(stage.name, round(duration, 4), round(peak_mb, 2)))
                performance_logger.info(
                    "job=%s stage=%s duration_sec=%.3f peak_mem_mb=%.2f",
                    context.job_id,
                    stage.name,
                    duration,
                    peak_mb,
                )

                if self._on_progress is not None:
                    self._on_progress(
                        StageProgress(
                            stage=stage.name,
                            stage_index=index,
                            total_stages=total,
                            progress=round(index / total * 100),
                            duration_seconds=duration,
                        )
                    )
                pipeline_logger.info("job=%s stage=%s finished in %.3fs", context.job_id, stage.name, duration)
        finally:
            if tracing:
                tracemalloc.stop()
