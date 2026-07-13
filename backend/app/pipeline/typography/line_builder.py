"""Line Builder (ADR-011, Phase 2).

The foundation the Paragraph Builder stands on: paragraphs are groups of
lines, runs live inside lines. Today a PDF "line" is already the extraction
unit (`TextBlock`), so this builder adopts each TextBlock as a Line node,
delegating its internal style structure to the Run Builder and preserving the
line's measured baseline/ascent/descent (never estimated). When extraction
moves to a raw glyph stream, the glyph→line clustering lands here without any
consumer changing.
"""

import uuid

from app.pipeline.elements.font import FontResource
from app.pipeline.elements.line import Line
from app.pipeline.elements.textbox import TextBlock
from app.pipeline.typography.run_builder import build_runs
from app.pipeline.typography.word_builder import build_words


def build_line(block: TextBlock, line_index: int, fonts_by_id: dict[str, FontResource]) -> Line:
    runs = build_runs(block, fonts_by_id)
    return Line(
        id=str(uuid.uuid4()),
        bbox=block.bbox,
        baseline_y=block.origin_y,
        ascent=block.ascender * block.font_size,
        descent=block.descender * block.font_size,
        leading=block.line_height,
        line_index=line_index,
        runs=runs,
        # Lexical words reconstructed from the runs; PyMuPDF words (block.words)
        # are geometry hints only (Phase 2.6).
        words=build_words(runs, block.origin_y, block.words),
    )
