"""Run Builder (ADR-011, Phase 2).

Collapses a line's style spans into the fewest runs that preserve every
genuine style change. Merge rule: adjacent spans join iff they render
identically — same *visual* font identity (font_identity.visual_style_key,
which ignores subset name / object id), size, and color. A real style change
(bold, italic, color, size, family) always splits, even mid-word; a
subset-only split (`Times` extracted as two subsets of the same face) merges.

Input is the frozen extraction model (TextBlock → TextSpan/WordBox); output is
Rich-IDM Run nodes. The builder never invents or drops characters: the
concatenated run text equals the concatenated span text (asserted by the
stage's fidelity check).
"""

import statistics
import uuid

from app.core.enums import ReconstructionMode
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.run import Run
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.typography.font_identity import is_bold, is_italic, visual_style_key


def _merge_key(span: TextSpan, fonts_by_id: dict[str, FontResource]) -> tuple:
    """Full visual identity of a span within a line. Rotation/writing-direction
    are constant across a line, so they need not enter the key here. Baseline
    `rise` IS part of identity: a raised span (superscript-like placement,
    measured from texttrace) renders at different geometry and must never
    merge with baseline text."""
    font = fonts_by_id.get(span.font_id or "")
    return (visual_style_key(font), round(span.font_size, 2), span.color, round(span.rise, 1))


def _run_from_spans(
    spans: list[TextSpan],
    block: TextBlock,
    fonts_by_id: dict[str, FontResource],
) -> Run:
    lead = spans[0]
    font = fonts_by_id.get(lead.font_id or "")
    text = "".join(s.text for s in spans)
    # Genuine measured tracking (Issue 002B): spans merged into one run share
    # visual identity, so they should carry the same measured value; the
    # median is a defensive aggregate against any single mismatch.
    tracking = [s.letter_spacing for s in spans if s.letter_spacing]
    letter_spacing = statistics.median(tracking) if tracking else 0.0
    return Run(
        id=str(uuid.uuid4()),
        # Runs own style, not geometry (Phase 2.6): the line box is a sufficient
        # bbox for a run; precise per-word geometry lives on the Line's words.
        bbox=BoundingBox(x=block.bbox.x, y=block.bbox.y, width=block.bbox.width, height=block.bbox.height),
        text=text,
        font_id=lead.font_id,
        font_size=lead.font_size,
        color=lead.color,
        weight=700 if (font and is_bold(font)) else 400,
        italic=bool(font and is_italic(font)),
        opacity=1.0,
        render_mode=block.render_mode,
        rotation=block.rotation,
        writing_mode="horizontal-tb",
        language=None,
        letter_spacing=round(letter_spacing, 3),
        rise=lead.rise,  # measured baseline rise (spans with differing rise never merge)
        mode=ReconstructionMode.RUN.value,
    )


def build_runs(block: TextBlock, fonts_by_id: dict[str, FontResource]) -> list[Run]:
    """Merge a line's spans into visual-identity runs. Words are NOT attached
    here — they are reconstructed from these runs by the Word Builder (Phase
    2.6), so a word can never be misrouted to the wrong same-family run."""
    spans = block.spans or [
        TextSpan(text=block.text, font_id=block.font_id, font_size=block.font_size, color=block.color)
    ]
    spans = [s for s in spans if s.text]
    if not spans:
        return []

    groups: list[list[TextSpan]] = [[spans[0]]]
    last_key = _merge_key(spans[0], fonts_by_id)
    for span in spans[1:]:
        key = _merge_key(span, fonts_by_id)
        if key == last_key:
            groups[-1].append(span)
        else:
            groups.append([span])
            last_key = key

    return [_run_from_spans(group, block, fonts_by_id) for group in groups]
