"""Typography Reconstruction v1 (Issues 002A/002B): relative escalation
tolerance + genuine tracking consumed as a known input, not re-derived."""

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.typography.adaptive_reconstruction import (
    AdaptiveReconstructionEngine,
    WORD_TOLERANCE_PX,
    word_tolerance_px,
)
from app.pipeline.typography.font_metrics import FontMetrics
from app.pipeline.typography.run_builder import build_runs

UPM = 1000


def _metrics(advances: dict[str, int]) -> FontMetrics:
    cmap = {ord(c): c for c in advances}
    return FontMetrics(cmap=cmap, advances={c: (a, 0) for c, a in advances.items()}, units_per_em=UPM)


# ---- 002A: relative tolerance ---------------------------------------------
# Calibrated from a real document (docs/ROAD_TO_PHASE4.md Issue 002A): the
# residual between PyMuPDF's ink-bbox word width and our advance-sum width is
# a near-constant ~2px regardless of glyph count — a measurement-definition
# gap, not accumulated per-glyph noise — plus a small per-glyph term.

def test_tolerance_is_never_below_the_original_floor() -> None:
    for n in range(1, 20):
        assert word_tolerance_px(n) >= WORD_TOLERANCE_PX


def test_tolerance_reflects_the_measured_bbox_advance_gap() -> None:
    # A single-glyph word already carries ~2px of definitional gap.
    assert word_tolerance_px(1) > 1.5


def test_tolerance_grows_only_mildly_with_glyph_count() -> None:
    # Long words get a WIDER but not run-away tolerance (mild per-glyph term).
    assert word_tolerance_px(11) > word_tolerance_px(1)
    assert word_tolerance_px(11) - word_tolerance_px(1) < 1.5


def test_tolerance_grows_monotonically() -> None:
    values = [word_tolerance_px(n) for n in range(1, 20)]
    assert values == sorted(values)


# ---- 002B: known tracking is consumed, not re-derived ---------------------

from app.pipeline.elements.textbox import WordBox  # noqa: E402


def _word(text: str, width: float, size: float = 10.0) -> WordBox:
    return WordBox(text=text, x=0.0, width=width, baseline_y=0.0, font_id="f1", font_size=size)


def test_known_tracking_prevents_escalation_when_it_explains_the_gap() -> None:
    eng = AdaptiveReconstructionEngine({"f1": _metrics({"A": 600, "B": 400})})
    # natural("AB") = 10.0px @ size10; +1px/glyph tracking known → expected 12.0.
    w = _word("AB", width=12.0)
    decision = eng.decide_word(w, char_spacing=1.0)
    assert decision.mode == "word"
    assert decision.reason == "tracking"
    assert decision.letter_spacing == 1.0


def test_known_tracking_reduces_but_may_not_eliminate_escalation() -> None:
    eng = AdaptiveReconstructionEngine({"f1": _metrics({"A": 600, "B": 400})})
    # expected with tracking = 10 + 1*2 = 12; actual 15 → still beyond
    # tolerance but a small (plausible), fittable residual on top of it.
    w = _word("AB", width=15.0)
    decision = eng.decide_word(w, char_spacing=1.0)
    assert decision.mode == "glyph"
    assert decision.reason == "tracking"
    assert decision.letter_spacing == 1.0 + (15.0 - 12.0) / 2  # known + residual


def test_implausible_residual_keeps_only_the_known_tracking() -> None:
    eng = AdaptiveReconstructionEngine({"f1": _metrics({"A": 600, "B": 400})})
    # expected with tracking = 12; actual 20 → residual (4px/glyph = 40% of
    # size) is implausible — trust the known tracking, don't fabricate more.
    w = _word("AB", width=20.0)
    decision = eng.decide_word(w, char_spacing=1.0)
    assert decision.mode == "glyph"
    assert decision.reason == "tracking"
    assert decision.letter_spacing == 1.0


def test_zero_char_spacing_behaves_exactly_as_before() -> None:
    eng = AdaptiveReconstructionEngine({"f1": _metrics({"A": 600, "B": 400})})
    w = _word("AB", width=10.05)
    decision = eng.decide_word(w)  # default char_spacing=0.0
    assert decision.mode == "word"
    assert decision.reason == "none"
    assert decision.letter_spacing == 0.0


# ---- Run Builder propagates measured tracking ------------------------------

def test_run_builder_sets_letter_spacing_from_spans() -> None:
    fonts = {"f1": FontResource(id="f1", original_name="Arial", family="Arial")}
    block = TextBlock(
        id="b1", page=1, bbox=BoundingBox(0, 0, 100, 12), text="tracked",
        spans=[TextSpan(text="tracked", font_id="f1", font_size=12.0, color="#000", letter_spacing=2.57)],
    )
    runs = build_runs(block, fonts)
    assert len(runs) == 1
    assert runs[0].letter_spacing == 2.57


def test_run_builder_defaults_to_zero_when_no_spans_have_tracking() -> None:
    fonts = {"f1": FontResource(id="f1", original_name="Arial", family="Arial")}
    block = TextBlock(
        id="b1", page=1, bbox=BoundingBox(0, 0, 100, 12), text="plain",
        spans=[TextSpan(text="plain", font_id="f1", font_size=12.0, color="#000")],
    )
    assert build_runs(block, fonts)[0].letter_spacing == 0.0
