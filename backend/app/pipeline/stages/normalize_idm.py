import logging
import time

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import Stage
from app.pipeline.typography.adaptive_reconstruction import AdaptiveReconstructionEngine
from app.pipeline.typography.font_metrics import (
    Base14Metrics,
    FontMetrics,
    base14_metrics_for,
    load_font_metrics,
    natural_text_width,
)
from app.pipeline.typography.geometry_normalizer import normalize_page_geometry
from app.services.storage_service import StorageService

# Backward-compatible re-exports: these lived here before the typography
# package existed; tests and callers still import them from this module.
__all__ = [
    "NormalizeIdmStage",
    "FontMetrics",
    "Base14Metrics",
    "base14_metrics_for",
    "load_font_metrics",
    "natural_text_width",
    "compute_spacing",
    "apply_adaptive_precision",
]

logger = logging.getLogger("layoutforge.pipeline")


def compute_spacing(block, metrics_by_font):  # noqa: ANN001 - thin compat shim
    """Compat shim for the pre-refactor line-fitting helper (used by tests).
    Delegates to the Adaptive Reconstruction Engine's line path."""
    return AdaptiveReconstructionEngine(metrics_by_font)._compute_line_spacing(block)


def apply_adaptive_precision(word, metrics_by_font):  # noqa: ANN001 - compat shim
    """Compat shim for the pre-M1.6 word helper. Delegates to the engine."""
    AdaptiveReconstructionEngine(metrics_by_font).reconstruct_word(word)


class NormalizeIdmStage(Stage):
    """Reconciles raw extraction output into the normalized IDM every output
    plugin can trust. Orchestrates two single-responsibility phases
    (ADR-006): the Geometry Normalizer (reading order + line metrics) and
    the Adaptive Reconstruction Engine (font-measured word/line
    reconstruction with mode/reason/confidence). The document-level
    reconstruction profile it produces is persisted for analytics/validation.

    (This stage will formally split into registered Geometry Normalizer /
    Typography Analyzer / Adaptive Reconstruction / Semantic Analyzer stages
    as the Semantic Analyzer's work — paragraphs/tables/math — materializes
    at M3+; today those would be hollow, so the split is staged.)"""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self._storage = storage_service

    @property
    def name(self) -> str:
        return PipelineStage.NORMALIZE_IDM.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "Extraction stages must run before NormalizeIdmStage"

        metrics_by_font = self._load_all_font_metrics(context)
        engine = AdaptiveReconstructionEngine(metrics_by_font)

        for page in context.document.pages:
            started = time.perf_counter()

            # Phase 1 — geometry (no fonts).
            normalize_page_geometry(page)

            # Phase 2 — adaptive reconstruction (font-measured).
            fitted = 0
            if metrics_by_font:
                for block in page.text_blocks:
                    if block.words:
                        for word in block.words:
                            engine.reconstruct_word(word)
                        fitted += 1
                    else:
                        engine.reconstruct_line(block)
                        fitted += 1

            logger.info(
                "page=%s normalize_idm text_blocks=%s images=%s reconstructed=%s duration_ms=%.1f",
                page.number,
                len(page.text_blocks),
                len(page.images),
                fitted,
                (time.perf_counter() - started) * 1000,
            )

        # Persist the document reconstruction profile for analytics/validation.
        context.document.reconstruction_profile = engine.profile.to_dict()
        engine.log_profile()

    def _load_all_font_metrics(self, context: PipelineContext) -> "dict[str, FontMetrics | Base14Metrics | None]":
        """One metrics load per font for the whole document (documents reuse
        a handful of fonts across thousands of pages). Extracted files via
        fontTools; non-embedded base-14 fonts via MuPDF's built-in tables."""
        if self._storage is None or context.document is None:
            return {}
        fonts_dir = self._storage.fonts_dir(context.project_id)
        metrics: dict[str, FontMetrics | Base14Metrics | None] = {}
        for font in context.document.fonts:
            if font.filename:
                metrics[font.id] = load_font_metrics(fonts_dir / font.filename)
            else:
                metrics[font.id] = base14_metrics_for(font)
        return metrics
