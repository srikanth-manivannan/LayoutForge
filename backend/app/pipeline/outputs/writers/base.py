"""Writer base (ADR-011, Phase 3)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.pipeline.outputs.writers.context import Target, WriterContext


@dataclass
class WriterResult:
    """What a writer produces: one rendered document per page and the shared
    stylesheet (deduplicated by the Style Registry)."""

    pages: list[tuple[int, str]]  # (page_number, html)
    stylesheet: str


class Writer(ABC):
    """Compiles a Rich-IDM `Document` (via WriterContext) to one output
    format. A writer reads only the model and never repairs it (LFS §5)."""

    target: Target

    @abstractmethod
    def write(self, ctx: WriterContext) -> WriterResult:
        ...
