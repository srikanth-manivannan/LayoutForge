"""Character-spacing (Tc) reconstruction — Rendering Accuracy v1, Issue 002B.

Reconstructs genuine PDF character spacing so it becomes real document
typography (`TextSpan.letter_spacing`, applied as CSS letter-spacing) instead
of an ad hoc per-word width-fitting correction. Ground truth comes from
PyMuPDF `get_texttrace()`, which reports the RESOLVED glyph origins — the
PDF's actual pen advances, already including Tc/Tw/Tz/kerning — so this reads
the net effect directly rather than tokenizing raw content-stream operators
(more robust: some PDFs achieve spacing via `TJ` array micro-adjustments
rather than an explicit `Tc`, and the resolved origins capture either).

Matching: a texttrace SPAN is not one visual line — PyMuPDF only starts a new
span on a graphics-state change, so an entire same-style paragraph is often
ONE span covering several extracted lines back-to-back with no separator
(confirmed on a real document: a span's text read
`"...Jim BentonAll rights reserved..."`, two lines concatenated). Matching
must therefore work at PAGE granularity: all texttrace spans are flattened
into one ordered per-character stream, and each extracted line (`TextBlock`)
is located as an exact SUBSTRING of that stream, anchored by baseline y. Any
line that can't be found this way (rotation, RTL, no match) is left with
letter_spacing 0.0 — a safe bail-out, never a guess.
"""

import math
import statistics
from dataclasses import dataclass

from app.pipeline.elements.textbox import TextBlock

_MIN_PAIRS = 3
_NOISE_FLOOR_PX = 0.15   # an offset smaller than this is sub-pixel noise
_MAX_RESIDUAL_RATIO = 0.35  # residual stdev must be well below the offset


@dataclass(frozen=True)
class WordMeasurement:
    """Per-word ACTUAL typography measured from the PDF's resolved glyph
    origins (Typography Measurement Engine v2, M-R2). Advance-to-advance —
    never ink-bbox — so it is directly comparable to `natural_text_width`:

    - `advance_px`  — pen extent: first glyph origin → pen after last glyph
      (= the following stream character's origin);
    - `tracking_px` — median per-glyph offset over nominal advances (the
      word's own Tc/tracking, per WORD, not per span);
    - `residual_px` — RMS of per-glyph offsets about that median: ~0 means a
      uniform offset (CSS letter-spacing reproduces the word exactly);
      large means genuinely non-uniform internal geometry (kerning/TJ);
    - `glyph_count` — offsets actually measured (may exclude a line-final
      glyph whose following pen position is unknown)."""

    advance_px: float
    tracking_px: float
    residual_px: float
    glyph_count: int


def estimate_tracking(pairs: list[tuple[float, float]]) -> float:
    """`pairs` = [(actual_px, nominal_px), …] for consecutive non-space glyphs
    within ONE style span. Returns the estimated constant per-glyph tracking
    (px) — ONLY when the residual pattern is confidently explained by a
    constant additive offset; 0.0 otherwise (never guess)."""
    pairs = [(a, n) for a, n in pairs if n > 0]
    if len(pairs) < _MIN_PAIRS:
        return 0.0
    diffs = [a - n for a, n in pairs]
    median = statistics.median(diffs)
    if abs(median) < _NOISE_FLOOR_PX:
        return 0.0
    residual = statistics.pstdev([d - median for d in diffs])
    if residual > _MAX_RESIDUAL_RATIO * abs(median) + 0.1:
        return 0.0  # not a clean constant offset — don't attribute it
    return round(median, 3)


def _page_char_stream(texttrace_spans: list[dict]) -> list[tuple[str, float, float]]:
    """Every glyph on the page, in texttrace emission order, as (char, x, y).
    Spans are NOT line boundaries (see module docstring) — this stream must be
    searched by content, not sliced by span."""
    stream: list[tuple[str, float, float]] = []
    for span in texttrace_spans:
        for code, _gid, origin, _bbox in span.get("chars", []):
            if code:
                stream.append((chr(code), origin[0], origin[1]))
    return stream


# PyMuPDF's two extraction paths disagree on space codepoints: get_text()
# may report a Unicode space variant (U+200A hair space, via ToUnicode) where
# get_texttrace() reports the raw U+0020 — confirmed byte-for-byte in the
# field ('Tot the…' vs 'Tot the…'), which silently broke line matching
# (and therefore Tc/rise/word measurement) for exactly those lines. Matching
# folds every Unicode space separator to ' ' on BOTH sides — a 1:1 mapping,
# so stream offsets remain valid for geometry.
_SPACE_FOLD = {c: 0x20 for c in (
    0x00A0, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007,
    0x2008, 0x2009, 0x200A, 0x202F, 0x205F, 0x3000,
)}


def _fold_spaces(text: str) -> str:
    return text.translate(_SPACE_FOLD)


def _locate_line(
    block: TextBlock,
    page_text: str,
    page_stream: list[tuple[str, float, float]],
    tolerance_y: float = 1.5,
) -> int | None:
    """Index of `block.text`'s first character in the page's flattened glyph
    stream, anchored by baseline y (disambiguates repeated text like "the"
    appearing more than once on a page). Space variants are folded on both
    sides before matching (see _SPACE_FOLD). None = no confident match."""
    text = _fold_spaces(block.text)
    if block.rotation != 0.0 or block.writing_direction != "ltr" or not text:
        return None
    haystack = _fold_spaces(page_text)
    start = 0
    while True:
        index = haystack.find(text, start)
        if index == -1:
            return None
        if abs(page_stream[index][2] - block.origin_y) <= tolerance_y:
            return index
        start = index + 1


def _line_char_origins(
    block: TextBlock,
    page_text: str,
    page_stream: list[tuple[str, float, float]],
    tolerance_y: float = 1.5,
) -> list[float] | None:
    """Per-character x-origins for `block.text` (see _locate_line)."""
    index = _locate_line(block, page_text, page_stream, tolerance_y)
    if index is None:
        return None
    return [page_stream[index + offset][1] for offset in range(len(block.text))]


def analyze_block_tracking(
    block: TextBlock,
    page_text: str,
    page_stream: list[tuple[str, float, float]],
    metrics_by_font: dict,
) -> list[float]:
    """Per-span letter_spacing (px) for `block.spans`, same order. All 0.0 if
    the line couldn't be confidently located or a span is too short/unmeasurable."""
    origins = _line_char_origins(block, page_text, page_stream)
    if origins is None:
        return [0.0] * len(block.spans)
    advances = [origins[i + 1] - origins[i] for i in range(len(origins) - 1)]

    results: list[float] = []
    cursor = 0
    for span in block.spans:
        span_len = len(span.text)
        metrics = metrics_by_font.get(span.font_id or "")
        # This span's own glyphs' advances only (excludes the boundary
        # advance into the NEXT span, which may carry a different Tc).
        span_advances = advances[cursor:cursor + span_len - 1] if span_len > 0 else []
        cursor += span_len
        if metrics is None or not span_advances:
            results.append(0.0)
            continue
        pairs: list[tuple[float, float]] = []
        for offset, actual in enumerate(span_advances):
            ch = span.text[offset]
            if ch.isspace():
                continue
            nominal_units = metrics.advance(ch)
            if nominal_units is None:
                continue
            pairs.append((actual, nominal_units / metrics.units_per_em * span.font_size))
        results.append(estimate_tracking(pairs))
    return results


def token_letter_spacing(block: TextBlock) -> list[float]:
    """Per-token (whitespace-split) letter_spacing for `block.text`, in
    left-to-right order — the same order `WordBox`es come out in (both derive
    from the same reading order), so callers can zip them directly. Reads
    `block.spans[i].letter_spacing` (already populated by
    `analyze_page_tracking`), located by each token's start character offset
    against the spans' cumulative text-length ranges — no geometry needed."""
    boundaries: list[tuple[int, int, float]] = []
    cursor = 0
    for span in block.spans:
        boundaries.append((cursor, cursor + len(span.text), span.letter_spacing))
        cursor += len(span.text)

    def spacing_at(index: int) -> float:
        for start, end, spacing in boundaries:
            if start <= index < end:
                return spacing
        return 0.0

    result: list[float] = []
    text = block.text
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        start = index
        while index < len(text) and not text[index].isspace():
            index += 1
        result.append(spacing_at(start))
    return result


def _char_nominals(block: TextBlock, metrics_by_font: dict) -> list[float | None]:
    """Per-character nominal advance (px) across `block.text`, using each
    character's OWN span's font/size (a word may cross spans). None where the
    font is unmeasurable or the glyph is missing."""
    nominals: list[float | None] = []
    for span in block.spans:
        metrics = metrics_by_font.get(span.font_id or "")
        for ch in span.text:
            if metrics is None:
                nominals.append(None)
                continue
            units = metrics.advance(ch)
            nominals.append(None if units is None else units / metrics.units_per_em * span.font_size)
    # spans may not cover block.text exactly on malformed input — pad safely.
    while len(nominals) < len(block.text):
        nominals.append(None)
    return nominals


def measure_block_words(
    block: TextBlock,
    page_text: str,
    page_stream: list[tuple[str, float, float]],
    metrics_by_font: dict,
    tolerance_y: float = 1.5,
) -> "list[WordMeasurement | None]":
    """One WordMeasurement per whitespace-separated token of `block.text`
    (same order as the block's WordBoxes), or None where the word can't be
    measured confidently — bail-out-safe, never a guess."""
    token_count = len(block.text.split())
    start_index = _locate_line(block, page_text, page_stream, tolerance_y) if block.spans else None
    if start_index is None:
        return [None] * token_count

    nominals = _char_nominals(block, metrics_by_font)
    text = block.text
    line_len = len(text)

    def origin(offset: int) -> float | None:
        """x-origin of the char at line offset; for offset == line_len, the
        pen position AFTER the line's last glyph (the next stream char's
        origin, if it shares the baseline — texttrace order is pen order)."""
        stream_index = start_index + offset
        if stream_index >= len(page_stream):
            return None
        char, x, y = page_stream[stream_index]
        if offset == line_len and abs(y - block.origin_y) > tolerance_y:
            return None  # next char is on another line — pen extent unknown
        return x

    results: list[WordMeasurement | None] = []
    offset = 0
    while offset < line_len:
        if text[offset].isspace():
            offset += 1
            continue
        start = offset
        while offset < line_len and not text[offset].isspace():
            offset += 1
        end = offset  # token = text[start:end]

        offsets: list[float] = []
        measurable = True
        for i in range(start, end):
            actual_start, actual_end = origin(i), origin(i + 1)
            if actual_start is None:
                measurable = False
                break
            if actual_end is None:
                break  # line-final glyph without a following pen position — use the pairs we have
            nominal = nominals[i]
            if nominal is None:
                measurable = False
                break
            offsets.append((actual_end - actual_start) - nominal)

        first = origin(start)
        after_last = origin(end)
        if not measurable or not offsets or first is None:
            results.append(None)
            continue

        tracking = statistics.median(offsets)
        residual = math.sqrt(sum((o - tracking) ** 2 for o in offsets) / len(offsets))
        if after_last is not None:
            advance = after_last - first
        else:
            # Line-final word: extend the measured glyphs by the last glyph's
            # nominal advance + the fitted tracking.
            last_nominal = nominals[end - 1]
            if last_nominal is None:
                results.append(None)
                continue
            advance = (origin(end - 1) - first) + last_nominal + tracking
        results.append(WordMeasurement(
            advance_px=round(advance, 3),
            tracking_px=round(tracking, 3),
            residual_px=round(residual, 3),
            glyph_count=len(offsets),
        ))
    return results


_RISE_NOISE_PX = 0.5  # baseline offsets below this are sub-pixel noise


def measure_span_rises(
    block: TextBlock,
    page_text: str,
    page_stream: list[tuple[str, float, float]],
    tolerance_y: float | None = None,
) -> list[float]:
    """Per-span baseline rise (px, positive = raised above the line's main
    baseline), measured from the matched glyph stream's y-origins. All 0.0 if
    the line can't be confidently located — never guessed.

    The match tolerance must EXCEED the largest rise we intend to measure —
    a raised span's own glyphs may anchor the substring match. Default: half
    the block's font size."""
    tolerance = tolerance_y if tolerance_y is not None else max(1.5, block.font_size * 0.5)
    index = _locate_line(block, page_text, page_stream, tolerance)
    if index is None:
        return [0.0] * len(block.spans)
    rises: list[float] = []
    cursor = 0
    for span in block.spans:
        ys = [
            page_stream[index + cursor + offset][2]
            for offset, ch in enumerate(span.text)
            if not ch.isspace()
        ]
        cursor += len(span.text)
        if not ys:
            rises.append(0.0)
            continue
        # PDF y grows downward: baseline above the line's = smaller y = rise UP.
        rise = block.origin_y - statistics.median(ys)
        rises.append(round(rise, 3) if abs(rise) >= _RISE_NOISE_PX else 0.0)
    return rises


def analyze_page_typography(
    blocks: list[TextBlock], texttrace_spans: list[dict], metrics_by_font: dict
) -> dict[str, "list[WordMeasurement | None]"]:
    """One pass per page (the stream is built once): sets span-level
    letter_spacing (Tc, Issue 002B) AND baseline `rise` (Renderer Geometry
    Investigation) in place, AND returns per-block word measurements keyed by
    block id (Typography Measurement Engine v2, M-R2). Unmatched/unmeasurable
    lines keep 0.0 / None — the fallback paths handle them unchanged."""
    stream = _page_char_stream(texttrace_spans)
    page_text = "".join(c for c, _x, _y in stream)
    measurements: dict[str, list[WordMeasurement | None]] = {}
    for block in blocks:
        if not block.spans:
            continue
        spacing = analyze_block_tracking(block, page_text, stream, metrics_by_font)
        rises = measure_span_rises(block, page_text, stream)
        for span, value, rise in zip(block.spans, spacing, rises):
            span.letter_spacing = value
            span.rise = rise
        measurements[block.id] = measure_block_words(block, page_text, stream, metrics_by_font)
    return measurements


def analyze_page_tracking(blocks: list[TextBlock], texttrace_spans: list[dict], metrics_by_font: dict) -> None:
    """Backward-compatible wrapper: span-level Tc only (tests use this)."""
    analyze_page_typography(blocks, texttrace_spans, metrics_by_font)
