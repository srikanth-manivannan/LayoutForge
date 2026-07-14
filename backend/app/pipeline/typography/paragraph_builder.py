"""Paragraph Builder (ADR-011, Phase 2; LFS §5 Document Intelligence).

Groups a region's lines into paragraphs by **accumulating layout evidence**,
not by any single rule and never from PDF drawing operators. For each adjacent
line pair a set of weighted signals votes in [-1, +1] (+ = same paragraph,
- = break); the weighted consensus becomes a merge probability, and lines
merge while it stays above threshold. Every emitted Paragraph records its
`confidence` and the `signals` that supported it, so Validation can show
"Paragraph 94% · ✓ baseline ✓ indent ✓ font ⚠ hyphen" (mirrors the Adaptive
Reconstruction Engine, ADR-002).

Signals are a registry: today's set is baseline rhythm, vertical spacing,
left-edge continuity, font continuity, hyphenation, and line fill. List
markers, columns, widow/orphan, and language continuity slot in here as later
work packages land, without touching the builder or its consumers.
"""

import uuid
from collections import Counter
from dataclasses import dataclass

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.line import Line
from app.pipeline.elements.paragraph import Paragraph
from app.pipeline.typography.font_identity import visual_style_key

# A merge probability at/above this keeps two lines in one paragraph; below it
# they split. The gray band around it (±_AMBIGUOUS) is where the grouping is
# uncertain and the paragraph is flagged for review.
_MERGE_THRESHOLD = 0.6
_AMBIGUOUS = 0.12


@dataclass
class Vote:
    name: str
    vote: float  # [-1, +1]; + supports same-paragraph, - supports a break
    weight: float


@dataclass
class _Ctx:
    """Column reference shared by signals: the left/right text edges of the
    line set being grouped, so 'full line' vs 'short line' is measured against
    the actual column, not the page."""

    col_left: float
    col_right: float


def _dominant_run(line: Line):
    return line.runs[0] if line.runs else None


def _sig_baseline_rhythm(prev: Line, curr: Line, ctx: _Ctx) -> Vote | None:
    expected = prev.leading or curr.leading
    if expected <= 0:
        return None
    gap = curr.baseline_y - prev.baseline_y
    if gap <= 0:  # not a vertical successor (overlap / different column)
        return Vote("baseline", -1.0, 3.0)
    ratio = gap / expected
    if ratio <= 1.15:
        vote = 1.0
    elif ratio >= 1.8:
        vote = -1.0
    else:  # 1.15 → 1.8 linearly maps +0.6 → -1
        vote = 0.6 - (ratio - 1.15) / (1.8 - 1.15) * 1.6
    return Vote("baseline", max(-1.0, min(1.0, vote)), 3.0)


def _sig_vertical_spacing(prev: Line, curr: Line, ctx: _Ctx) -> Vote | None:
    expected = prev.leading or curr.leading
    if expected <= 0:
        return None
    extra = (curr.baseline_y - prev.baseline_y) - expected
    if extra <= 0.2 * expected:
        return Vote("spacing", 0.5, 1.5)
    return Vote("spacing", max(-1.0, -extra / expected), 1.5)


def _sig_left_edge(prev: Line, curr: Line, ctx: _Ctx) -> Vote | None:
    size = (_dominant_run(curr).font_size if _dominant_run(curr) else 0.0) or 10.0
    tol = max(0.15 * size, 2.0)
    dx = curr.bbox.x - prev.bbox.x
    if abs(dx) <= tol:
        return Vote("indent", 1.0, 2.0)
    if dx > tol:  # curr indented → likely a new paragraph's first-line indent
        return Vote("indent", -0.6, 2.0)
    return Vote("indent", -0.3, 2.0)  # curr further left than prev


def _sig_font_continuity(prev: Line, curr: Line, ctx: _Ctx) -> Vote | None:
    pr, cr = _dominant_run(prev), _dominant_run(curr)
    if pr is None or cr is None:
        return None
    size_ratio = cr.font_size / pr.font_size if pr.font_size else 1.0
    same_family = (pr.font_id, pr.italic, pr.weight) == (cr.font_id, cr.italic, cr.weight)
    if 0.95 <= size_ratio <= 1.05 and same_family:
        return Vote("font", 1.0, 2.5)
    if size_ratio > 1.15 or size_ratio < 0.87:  # heading / subhead break
        return Vote("font", -1.0, 2.5)
    return Vote("font", -0.6, 2.5)


def _sig_hyphenation(prev: Line, curr: Line, ctx: _Ctx) -> Vote | None:
    text = prev.runs[-1].text.rstrip() if prev.runs else ""
    if text.endswith("-") or text.endswith("­"):
        return Vote("hyphen", 1.0, 3.0)  # word continues onto curr → same paragraph
    return None  # not applicable → contributes no evidence


def _sig_line_fill(prev: Line, curr: Line, ctx: _Ctx) -> Vote | None:
    col_w = ctx.col_right - ctx.col_left
    if col_w <= 0:
        return None
    prev_right = prev.bbox.x + prev.bbox.width
    fill = (prev_right - ctx.col_left) / col_w
    if fill >= 0.92:  # prev fills the column → mid-paragraph line
        return Vote("fill", 0.5, 1.0)
    if fill <= 0.6:  # prev is short → could be a paragraph's last line
        return Vote("fill", -0.3, 1.0)
    return None


_SIGNALS = (
    _sig_baseline_rhythm,
    _sig_vertical_spacing,
    _sig_left_edge,
    _sig_font_continuity,
    _sig_hyphenation,
    _sig_line_fill,
)


def _merge_probability(prev: Line, curr: Line, ctx: _Ctx) -> tuple[float, list[Vote]]:
    votes = [v for sig in _SIGNALS if (v := sig(prev, curr, ctx)) is not None]
    total_w = sum(v.weight for v in votes)
    if total_w == 0:
        return 0.5, votes
    consensus = sum(v.vote * v.weight for v in votes) / total_w  # [-1, +1]
    return (consensus + 1.0) / 2.0, votes  # → [0, 1]


def _alignment(lines: list[Line], ctx: _Ctx) -> str:
    tol = 3.0
    lefts = [line.bbox.x for line in lines]
    rights = [line.bbox.x + line.bbox.width for line in lines]
    left_flush = all(abs(x - ctx.col_left) <= tol for x in lefts)
    right_flush = all(abs(ctx.col_right - r) <= tol for r in rights)
    if left_flush and right_flush and len(lines) > 1:
        return "justify"
    if right_flush and not left_flush:
        return "right"
    if not left_flush and not right_flush:
        centers = [abs((line.bbox.x - ctx.col_left) - (ctx.col_right - (line.bbox.x + line.bbox.width))) for line in lines]
        if all(c <= 2 * tol for c in centers):
            return "center"
    return "left"


def _make_paragraph(lines: list[Line], merges: list[tuple[float, list[Vote]]], ctx: _Ctx) -> Paragraph:
    xs = [line.bbox.x for line in lines]
    ys = [line.bbox.y for line in lines]
    rights = [line.bbox.x + line.bbox.width for line in lines]
    bottoms = [line.bbox.y + line.bbox.height for line in lines]
    left, top = min(xs), min(ys)
    bbox = BoundingBox(x=left, y=top, width=max(rights) - left, height=max(bottoms) - top)

    if merges:
        confidence = round(sum(p for p, _ in merges) / len(merges), 3)
        supporting = Counter()
        for _, votes in merges:
            for v in votes:
                if v.vote > 0:
                    supporting[v.name] += 1
        signals = [name for name, _ in supporting.most_common()]
        ambiguous = any(abs(p - _MERGE_THRESHOLD) <= _AMBIGUOUS for p, _ in merges)
        reason = "ambiguous_boundary" if ambiguous else "grouped"
    else:
        confidence = 1.0
        signals = []
        reason = "single_line"

    # line_height drives the browser's CSS line-height for the whole flowed
    # paragraph, so it must be the REAL measured baseline-to-baseline gap
    # whenever one exists — not a per-line font-metric estimate (ascender -
    # descender) * font_size, which approximates a single isolated line's
    # natural height but is not the PDF's actual inter-line spacing. A
    # multi-line paragraph already carries real spacing in its own lines'
    # baseline_y values; using anything else here silently inflates the
    # paragraph's flowed height, which then pushes every paragraph after it
    # further down the page — the same class of defect as inventing/
    # discarding measured geometry in the Instruction Builder (2026-07-14).
    baseline_gaps = sorted(
        curr.baseline_y - prev.baseline_y
        for prev, curr in zip(lines, lines[1:])
        if curr.baseline_y > prev.baseline_y
    )
    if baseline_gaps:
        line_height = round(baseline_gaps[len(baseline_gaps) // 2], 2)
    else:
        # Single-line paragraph (or no valid consecutive baselines): no real
        # gap to measure, fall back to the font-metric estimate each line
        # already carries (Line.leading, from geometry_normalizer.py).
        leadings = sorted(line.leading for line in lines if line.leading > 0)
        line_height = leadings[len(leadings) // 2] if leadings else 0.0
    return Paragraph(
        id=str(uuid.uuid4()),
        bbox=bbox,
        alignment=_alignment(lines, ctx),
        first_line_indent=round(lines[0].bbox.x - left, 2),
        line_height=line_height,
        leading=line_height,
        confidence=confidence,
        reason=reason,
        signals=signals,
        lines=lines,
    )


def build_paragraphs(lines: list[Line], fonts_by_id: dict[str, FontResource] | None = None) -> list[Paragraph]:
    """Group reading-ordered lines into paragraphs by weighted evidence."""
    lines = [line for line in lines if line.runs]
    if not lines:
        return []
    ctx = _Ctx(
        col_left=min(line.bbox.x for line in lines),
        col_right=max(line.bbox.x + line.bbox.width for line in lines),
    )

    paragraphs: list[Paragraph] = []
    group: list[Line] = [lines[0]]
    merges: list[tuple[float, list[Vote]]] = []
    for prev, curr in zip(lines, lines[1:]):
        prob, votes = _merge_probability(prev, curr, ctx)
        if prob >= _MERGE_THRESHOLD:
            group.append(curr)
            merges.append((prob, votes))
        else:
            paragraphs.append(_make_paragraph(group, merges, ctx))
            group, merges = [curr], []
    paragraphs.append(_make_paragraph(group, merges, ctx))
    for index, paragraph in enumerate(paragraphs):
        for line in paragraph.lines:
            line.line_index = paragraph.lines.index(line)
    return paragraphs
