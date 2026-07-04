from abc import ABC, abstractmethod

from app.pipeline.context import PipelineContext


class Stage(ABC):
    """A single step in the conversion pipeline. Stages mutate the
    PipelineContext (typically by populating or reading context.document)
    and must not assume a specific execution backend — today they run via
    FastAPI BackgroundTasks, but the same Stage implementations must work
    unchanged behind a Celery/RQ/Kubernetes Jobs runner later."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def run(self, context: PipelineContext) -> None:
        ...
