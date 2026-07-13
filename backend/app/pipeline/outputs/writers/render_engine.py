"""Render Engine (ADR-011, Phase 3).

The single entry point that turns a Rich-IDM `Document` into an output. It
dispatches to the Writer registered for the context's target and knows nothing
format-specific itself — adding EPUB/XML/PML means registering a Writer, never
editing the engine or the model (ADR-005).
"""

from app.pipeline.outputs.writers.base import Writer, WriterResult
from app.pipeline.outputs.writers.context import Target, WriterContext
from app.pipeline.outputs.writers.html_writer import HtmlWriter


class UnsupportedTargetError(NotImplementedError):
    """Raised for a reserved target that has no Writer yet (EPUB/XML/PML)."""


class RenderEngine:
    def __init__(self, writers: dict[Target, Writer] | None = None) -> None:
        # Implemented writers. Fixed-Layout/EPUB/XML/PML are reserved seams
        # (M5) — registering one here is the only change needed to add it.
        self._writers: dict[Target, Writer] = writers or {Target.HTML: HtmlWriter()}

    def register(self, target: Target, writer: Writer) -> None:
        self._writers[target] = writer

    def render(self, ctx: WriterContext) -> WriterResult:
        writer = self._writers.get(ctx.target)
        if writer is None:
            raise UnsupportedTargetError(
                f"No writer registered for target '{ctx.target.value}' (reserved; lands with its milestone)"
            )
        return writer.write(ctx)
