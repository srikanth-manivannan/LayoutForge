"""Geometry Normalizer (docs/design/typography, ADR-006 pipeline layering).

Single responsibility: the geometry of a page's lines — reading order and
line metrics (baseline/leading) — with no font-measurement concerns. Runs
before the Adaptive Reconstruction Engine, which handles everything that
needs font metrics. Kept separate so each phase has one job and is
debuggable in isolation."""

from app.pipeline.elements.page import Page

_DEFAULT_LINE_HEIGHT_RATIO = 1.2
_READING_ORDER_ROW_TOLERANCE = 2.0  # px; lines within this many px of y share a row


def normalize_page_geometry(page: Page) -> None:
    """Assign reading order top→bottom/left→right and fill missing line
    heights from the font's real ascender/descender (falling back to the
    1.2× ratio only when unavailable). Mutates the page in place."""
    ordered = sorted(
        page.text_blocks,
        key=lambda block: (round(block.bbox.y / _READING_ORDER_ROW_TOLERANCE), block.bbox.x),
    )
    for order, block in enumerate(ordered):
        block.reading_order = order
        if block.line_height <= 0:
            metric_height = (block.ascender - block.descender) * block.font_size
            block.line_height = round(metric_height or block.font_size * _DEFAULT_LINE_HEIGHT_RATIO, 2)
    page.text_blocks = ordered
    page.fonts_used = sorted(set(page.fonts_used))
