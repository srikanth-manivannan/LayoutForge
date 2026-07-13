"""GenerateSemanticHtml stage (ADR-011, Phase 3b).

Renders the Rich IDM (`page.regions`) through the semantic writer into a
parallel `pages_semantic/` tree, gated behind `settings.use_rich_tree`
(default off). This exists so the new compiler can be validated against a real
corpus and diffed vs the legacy fixed-layout output *before* the legacy path
is retired (Phase 4) — enabling it changes no production behavior, only adds
files. A shared, deduplicated `semantic.css` is written once and linked by
every page.
"""

import logging
import time

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.outputs.writers.context import FeatureFlags, Target, WriterContext
from app.pipeline.outputs.writers.render_engine import RenderEngine
from app.pipeline.stages.base import Stage
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")


class GenerateSemanticHtmlStage(Stage):
    def __init__(
        self,
        storage_service: StorageService,
        *,
        enabled: bool = False,
        emit_debug_attributes: bool = False,
    ) -> None:
        self._storage = storage_service
        self._enabled = enabled
        self._emit_debug = emit_debug_attributes
        self._engine = RenderEngine()

    @property
    def name(self) -> str:
        return PipelineStage.GENERATE_SEMANTIC_HTML.value

    def run(self, context: PipelineContext) -> None:
        if not self._enabled:
            return  # legacy fixed-layout output remains the runtime default
        document = context.document
        assert document is not None, "Extraction stages must run before GenerateSemanticHtmlStage"

        started = time.perf_counter()
        flags = FeatureFlags(emit_debug_attributes=self._emit_debug)
        result = self._engine.render(WriterContext.create(document, target=Target.HTML, flags=flags))

        out_dir = self._storage.project_dir(context.project_id) / "pages_semantic"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "semantic.css").write_text(result.stylesheet, encoding="utf-8")
        for page_number, html in result.pages:
            (out_dir / f"page_{page_number:04d}.html").write_text(html, encoding="utf-8")

        logger.info(
            "project=%s generate_semantic_html pages=%s css_rules=%s duration_ms=%.1f",
            context.project_id,
            len(result.pages),
            result.stylesheet.count("{"),
            (time.perf_counter() - started) * 1000,
        )
