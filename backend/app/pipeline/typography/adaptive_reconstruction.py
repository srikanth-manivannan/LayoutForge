"""Adaptive Reconstruction Engine (docs/design/typography/12).

Reconstruct each object at the CHEAPEST level that reproduces it within
tolerance, and record WHY it escalated plus an internal CONFIDENCE — so the
engine is explainable and a 3,000-page book pays for glyph-level precision
only where measurement proves it necessary. Glyph reconstruction (M2) is a
CONSUMER of these decisions; it never recomputes them.

The name is deliberately broad: today it decides WORD ↔ GLYPH, but it will
grow to WORD → RUN → GLYPH → SVG → IMAGE as later milestones land."""

import logging
from dataclasses import dataclass, field

from app.core.enums import ReconstructionMode, ReconstructionReason
from app.pipeline.elements.textbox import TextBlock, WordBox
from app.pipeline.typography.font_metrics import (
    MAX_MISSING_CHAR_FRACTION,
    Base14Metrics,
    FontMetrics,
    natural_text_width,
)

logger = logging.getLogger("layoutforge.pipeline")

# ---------------------------------------------------------------------------
# PUBLIC API — frozen as of M1.7 (ADR-002). Every downstream consumer (M2
# glyph/precision reconstruction, validation, analytics, the editor) reads
# `ReconstructionDecision` and never re-derives its own interpretation.
# Stable surface: ReconstructionDecision, AdaptiveReconstructionEngine
# (.decide_word, .reconstruct_word, .reconstruct_line, .profile),
# ReconstructionProfile, classify_reason. Anything prefixed `_` is internal.
# ---------------------------------------------------------------------------
__all__ = [
    "ReconstructionDecision",
    "AdaptiveReconstructionEngine",
    "ReconstructionProfile",
    "classify_reason",
    "WORD_TOLERANCE_PX",
]


@dataclass(frozen=True)
class ReconstructionDecision:
    """The frozen contract the Adaptive Reconstruction Engine emits for one
    object. Immutable so no consumer can mutate a decision in place. Later
    stages CONSUME this — they never recompute mode/reason/confidence."""

    mode: str  # ReconstructionMode value
    reason: str  # ReconstructionReason value
    reconstruction_confidence: float  # [0,1], internal engineering metric
    expected_width: float  # px, from font metrics (unkerned advances)
    actual_width: float  # px, ground-truth PDF box
    width_error: float  # px, actual − expected
    tolerance: float  # px, the WORD/GLYPH threshold in force
    letter_spacing: float = 0.0  # interim per-char correction (GLYPH only)

# A word whose rendered natural width is within this many px of its true PDF
# box needs no correction — browser layout at the pinned x is already
# accurate (WORD). A larger error means uniform letter-spacing can't
# reproduce the word's internal advances; it escalates to GLYPH.
WORD_TOLERANCE_PX = 0.3
_MAX_SPACING_FRACTION_OF_SIZE = 0.25
_MIN_MEANINGFUL_SPACING = 0.01  # px

# Sequences that form ligatures in most text fonts — a strong signal that a
# word's width difference is ligature substitution rather than plain kerning.
_LIGATURE_SEQUENCES = ("ffi", "ffl", "ff", "fi", "fl")
_LIGATURE_CHARS = "ﬀﬁﬂﬃﬄ"  # ﬀ ﬁ ﬂ ﬃ ﬄ

MetricsByFont = "dict[str, FontMetrics | Base14Metrics | None]"


def classify_reason(text: str, error: float) -> str:
    """Attribute WHY a word escalated, from cheap signals. LIGATURE beats
    KERNING (ligature substitution changes width more than kerning);
    KERNING when the PDF rendered narrower than unkerned advances (kern
    pulled glyphs together); WIDTH_ERROR when wider (tracking/spacing)."""
    lowered = text.lower()
    if any(ch in _LIGATURE_CHARS for ch in text) or any(seq in lowered for seq in _LIGATURE_SEQUENCES):
        return ReconstructionReason.LIGATURE.value
    if error < 0:
        return ReconstructionReason.KERNING.value
    return ReconstructionReason.WIDTH_ERROR.value


@dataclass
class ReconstructionProfile:
    """Document-level analytics: how many objects at each level, and why
    they escalated. Gold for improving the engine and for Validation
    ("51,199 glyph words: 41k kerning, 6k ligatures, …")."""

    words: int = 0
    by_mode: dict[str, int] = field(default_factory=dict)
    by_reason: dict[str, int] = field(default_factory=dict)
    confidence_sum: float = 0.0
    # Character fidelity (additive, post-purge): every non-whitespace char
    # either paints in its own font or — when its glyph was unrecoverable
    # and therefore unmapped — paints via the fallback stack (SUBSTITUTED).
    # Painting nothing is impossible by construction, so chars_lost ≡ 0.
    chars_total: int = 0
    chars_substituted: int = 0

    def record(self, decision: "ReconstructionDecision") -> None:
        self.words += 1
        self.by_mode[decision.mode] = self.by_mode.get(decision.mode, 0) + 1
        if decision.reason != ReconstructionReason.NONE.value:
            self.by_reason[decision.reason] = self.by_reason.get(decision.reason, 0) + 1
        self.confidence_sum += decision.reconstruction_confidence

    def to_dict(self) -> dict:
        glyph = self.by_mode.get(ReconstructionMode.GLYPH.value, 0)
        return {
            "words": self.words,
            "by_mode": dict(self.by_mode),
            "by_reason": dict(self.by_reason),
            "glyph_fraction": round(glyph / self.words, 4) if self.words else 0.0,
            "mean_reconstruction_confidence": round(self.confidence_sum / self.words, 4) if self.words else 1.0,
            "chars_total": self.chars_total,
            "chars_substituted": self.chars_substituted,
            "chars_lost": 0,  # structurally guaranteed by the blank-mapping purge
            "character_substitution_rate": round(self.chars_substituted / self.chars_total, 6)
            if self.chars_total
            else 0.0,
        }


class AdaptiveReconstructionEngine:
    """Owns the reconstruct-level decision for words and lines. Stateless
    except for the profile it accumulates; one instance per document run."""

    def __init__(self, metrics_by_font: MetricsByFont) -> None:
        self._metrics = metrics_by_font
        self.profile = ReconstructionProfile()

    # ---- words (word-pinned lines, M1.5/M1.6/M1.7) ---------------------

    def decide_word(self, word: WordBox) -> ReconstructionDecision:
        """Pure decision for one word — the frozen contract (M1.7). No
        mutation; consumers (M2, validation, analytics) read this."""
        metrics = self._metrics.get(word.font_id or "")
        if metrics is None or not word.text:
            return ReconstructionDecision(
                mode=ReconstructionMode.WORD.value,
                reason=ReconstructionReason.UNKNOWN.value,
                reconstruction_confidence=0.7,  # unmeasurable font — left native
                expected_width=0.0,
                actual_width=word.width,
                width_error=0.0,
                tolerance=WORD_TOLERANCE_PX,
            )

        natural, missing = natural_text_width(word.text, word.font_size, metrics)
        if natural <= 0 or missing / len(word.text) > MAX_MISSING_CHAR_FRACTION:
            return ReconstructionDecision(
                mode=ReconstructionMode.WORD.value,
                reason=ReconstructionReason.FONT_SUBSET.value,
                reconstruction_confidence=0.6,  # glyphs missing from subset
                expected_width=round(natural, 3),
                actual_width=word.width,
                width_error=round(word.width - natural, 3),
                tolerance=WORD_TOLERANCE_PX,
            )

        error = word.width - natural
        if abs(error) <= WORD_TOLERANCE_PX:
            # WORD level — browser layout is already accurate.
            return ReconstructionDecision(
                mode=ReconstructionMode.WORD.value,
                reason=ReconstructionReason.NONE.value,
                reconstruction_confidence=round(max(0.0, 1.0 - abs(error) / max(word.width, 1.0)), 4),
                expected_width=round(natural, 3),
                actual_width=word.width,
                width_error=round(error, 3),
                tolerance=WORD_TOLERANCE_PX,
            )

        # Escalate to GLYPH; attribute the reason.
        reason = classify_reason(word.text, error)
        spacing = error / len(word.text)
        if abs(spacing) > _MAX_SPACING_FRACTION_OF_SIZE * max(word.font_size, 1.0):
            # Implausible correction — trust the pinned position, don't distort.
            return ReconstructionDecision(
                mode=ReconstructionMode.GLYPH.value,
                reason=reason,
                reconstruction_confidence=0.4,
                expected_width=round(natural, 3),
                actual_width=word.width,
                width_error=round(error, 3),
                tolerance=WORD_TOLERANCE_PX,
            )
        # Interim: letter-spacing makes WIDTH exact; glyph POSITIONS remain
        # approximate (uniform vs real kerning), so confidence is capped.
        return ReconstructionDecision(
            mode=ReconstructionMode.GLYPH.value,
            reason=reason,
            reconstruction_confidence=round(max(0.4, 0.9 - abs(spacing) / max(word.font_size, 1.0)), 4),
            expected_width=round(natural, 3),
            actual_width=word.width,
            width_error=round(error, 3),
            tolerance=WORD_TOLERANCE_PX,
            letter_spacing=round(spacing, 3),
        )

    def reconstruct_word(self, word: WordBox) -> ReconstructionDecision:
        """Decide and APPLY the decision to the word, recording it in the
        profile. Returns the decision so callers can also consume it."""
        decision = self.decide_word(word)
        word.mode = decision.mode
        word.reason = decision.reason
        word.reconstruction_confidence = decision.reconstruction_confidence
        word.width_error = decision.width_error
        word.letter_spacing = decision.letter_spacing
        self.profile.record(decision)
        self._count_character_fidelity(word)
        return decision

    def _count_character_fidelity(self, word: WordBox) -> None:
        """Post-purge accounting: a char absent from its font's cmap will
        paint via the fallback stack (substituted — visible, different
        font). Mapped chars paint in their own font. Nothing paints blank."""
        metrics = self._metrics.get(word.font_id or "")
        if metrics is None:
            return
        for char in word.text:
            if char.isspace():
                continue
            self.profile.chars_total += 1
            if metrics.advance(char) is None:
                self.profile.chars_substituted += 1

    # ---- lines (fallback for non-word-pinned blocks) -------------------

    def reconstruct_line(self, block: TextBlock) -> None:
        """Line-level width fitting for blocks without word boxes
        (rotated/RTL/unresolved). Distributes surplus to word-spacing for
        justified text, letter-spacing for spaceless runs."""
        spacing = self._compute_line_spacing(block)
        if spacing is not None:
            block.letter_spacing, block.word_spacing = spacing

    def _compute_line_spacing(self, block: TextBlock) -> tuple[float, float] | None:
        if block.rotation != 0 or block.writing_direction != "ltr":
            return None
        spans = block.spans or []
        if not spans or not block.text:
            return None
        natural = 0.0
        char_count = 0
        missing = 0
        for span in spans:
            if not span.text:
                continue
            metrics = self._metrics.get(span.font_id or "")
            if metrics is None:
                return None
            width, span_missing = natural_text_width(span.text, span.font_size or block.font_size, metrics)
            natural += width
            missing += span_missing
            char_count += len(span.text)
        if char_count == 0 or natural <= 0 or missing / char_count > MAX_MISSING_CHAR_FRACTION:
            return None
        surplus = block.bbox.width - natural
        space_count = block.text.count(" ")
        if space_count > 0:
            word_spacing = surplus / space_count
            if abs(word_spacing) < _MIN_MEANINGFUL_SPACING or abs(word_spacing) > max(block.font_size, 1.0):
                return None
            return (0.0, round(word_spacing, 3))
        spacing = surplus / char_count
        if abs(spacing) < _MIN_MEANINGFUL_SPACING or abs(spacing) > _MAX_SPACING_FRACTION_OF_SIZE * max(block.font_size, 1.0):
            return None
        return (round(spacing, 3), 0.0)

    def log_profile(self) -> None:
        p = self.profile
        if not p.words:
            return
        glyph = p.by_mode.get("glyph", 0)
        logger.info(
            "adaptive_reconstruction: %s words · %s glyph (%.1f%%) · %s word (%.1f%%) · reasons=%s · mean_conf=%.3f",
            p.words,
            glyph,
            100 * glyph / p.words,
            p.words - glyph,
            100 * (p.words - glyph) / p.words,
            p.by_reason,
            p.confidence_sum / p.words,
        )
