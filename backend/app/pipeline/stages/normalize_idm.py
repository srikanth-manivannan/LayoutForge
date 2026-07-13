import logging
import time

import fitz

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import Stage
from app.pipeline.typography.adaptive_reconstruction import AdaptiveReconstructionEngine
from app.pipeline.typography.character_spacing import analyze_page_typography, token_letter_spacing
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
        pdf = self._reopen_source_pdf(context) if metrics_by_font else None

        try:
            for page in context.document.pages:
                started = time.perf_counter()

                # Phase 1 — geometry (no fonts).
                normalize_page_geometry(page)

                # Phase 1.5 — measured typography (Issue 002B + M-R2): span-
                # level Tc AND per-word advance measurements from the PDF's
                # resolved glyph origins. Advisory: any mismatch/failure
                # leaves spans at 0.0 / measurements as None — never guessed.
                measurements: dict = {}
                if pdf is not None:
                    measurements = self._analyze_typography(pdf, page, metrics_by_font)

                # Phase 2 — adaptive reconstruction, consuming measured
                # typography as a known input rather than re-deriving it from
                # residual width error. Measured words decide advance-to-
                # advance (M-R2); unmeasured ones keep the bbox fallback.
                fitted = 0
                if metrics_by_font:
                    for block in page.text_blocks:
                        if block.words:
                            spacing_by_token = token_letter_spacing(block) if block.spans else []
                            word_measurements = measurements.get(block.id, [])
                            for index, word in enumerate(block.words):
                                char_spacing = spacing_by_token[index] if index < len(spacing_by_token) else 0.0
                                measurement = word_measurements[index] if index < len(word_measurements) else None
                                engine.reconstruct_word(word, char_spacing=char_spacing, measurement=measurement)
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
        finally:
            if pdf is not None:
                pdf.close()

        # Persist the document reconstruction profile for analytics/validation.
        context.document.reconstruction_profile = engine.profile.to_dict()
        engine.log_profile()

    def _reopen_source_pdf(self, context: PipelineContext) -> "fitz.Document | None":
        """Reopens the source PDF for character-spacing analysis (Issue
        002B) — the same independent-reopen pattern ExtractFontsStage/
        ExtractTextStage/RenderBackgroundsStage already use. Advisory: a
        missing/unreadable path disables tracking analysis, never fails the
        stage (tests routinely run NormalizeIdmStage with no PDF on disk)."""
        if not context.source_pdf_path:
            return None
        try:
            return fitz.open(context.source_pdf_path)
        except Exception:  # noqa: BLE001 - advisory; degrade to no tracking data
            logger.warning("normalize_idm: could not reopen source PDF for tracking analysis", exc_info=True)
            return None

    def _analyze_typography(self, pdf: "fitz.Document", page, metrics_by_font: dict) -> dict:
        try:
            pdf_page = pdf[page.number - 1]
            texttrace = pdf_page.get_texttrace()
        except Exception:  # noqa: BLE001 - advisory; one bad page must not abort the document
            logger.warning("page=%s typography analysis failed", page.number, exc_info=True)
            return {}
        return analyze_page_typography(page.text_blocks, texttrace, metrics_by_font)

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
