from abc import ABC, abstractmethod
from typing import Any

from app.pipeline.context import PipelineContext


class OutputPlugin(ABC):
    """Generates one output artifact (HTML, CSS, manifest, and in future
    EPUB/JSON/XML) by reading exclusively from context.document — the
    Internal Document Model. Output plugins must never import or reference
    the input adapter library (e.g. PyMuPDF/fitz). The return value is
    plugin-specific (e.g. CssOutputPlugin returns per-page file paths so its
    Stage can persist them) — callers should not assume a shape beyond what
    their own plugin documents."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def generate(self, context: PipelineContext) -> Any:
        ...
