"""Typography Measurement Engine v2 (M-R2b): per-word advance measurement
from resolved glyph origins, and advance-to-advance reconstruction decisions.
Measurement + reconstruction only — no renderer behavior is involved."""

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.textbox import TextBlock, TextSpan, WordBox
from app.pipeline.typography.adaptive_reconstruction import (
    ADVANCE_RESIDUAL_TOLERANCE_PX,
    AdaptiveReconstructionEngine,
)
from app.pipeline.typography.character_spacing import (
    WordMeasurement,
    _page_char_stream,
    measure_block_words,
)
from app.pipeline.typography.font_metrics import FontMetrics

UPM = 1000


def _metrics(advances: dict[str, int]) -> FontMetrics:
    cmap = {ord(c): c for c in advances}
    return FontMetrics(cmap=cmap, advances={c: (a, 0) for c, a in advances.items()}, units_per_em=UPM)


def _block(text: str, size: float = 10.0) -> TextBlock:
    return TextBlock(
        id="b1", page=1, bbox=BoundingBox(0, 30, 200, 12), text=text,
        origin_y=40.0, rotation=0.0, writing_direction="ltr", font_size=size,
        spans=[TextSpan(text=text, font_id="f1", font_size=size, color="#000")],
    )


def _stream_for(text: str, advances_px: list[float], y: float = 40.0):
    """Build a texttrace stream where char i sits at the cumulative advance
    position; len(advances_px) == len(text) (advance after each char)."""
    xs = [0.0]
    for advance in advances_px[:-1]:
        xs.append(xs[-1] + advance)
    chars = [(ord(ch), 0, (x, y), (x, y - 8, x + 8, y + 2)) for ch, x in zip(text, xs)]
    stream = _page_char_stream([{"chars": chars}])
    return "".join(c for c, _x, _y in stream), stream


# ---- measurement ------------------------------------------------------------

def test_uniform_tracking_measured_per_word() -> None:
    # "AB CD": A=6,B=4,C=5,D=5 nominal @size10; every glyph +2px tracking.
    metrics = {"f1": _metrics({"A": 600, "B": 400, "C": 500, "D": 500, " ": 300})}
    advances = [8.0, 6.0, 5.0, 7.0, 7.0]  # A,B,space,C,D — glyphs +2, space nominal+2
    page_text, stream = _stream_for("AB CD", advances)
    words = measure_block_words(_block("AB CD"), page_text, stream, metrics)
    assert len(words) == 2
    first = words[0]
    assert first is not None
    assert abs(first.tracking_px - 2.0) < 0.01
    assert first.residual_px < 0.01           # perfectly uniform
    assert abs(first.advance_px - 14.0) < 0.01  # 8 + 6 (pen extent to the space)


def test_nonuniform_kerning_yields_large_residual() -> None:
    metrics = {"f1": _metrics({"A": 600, "B": 400, "C": 500})}
    # A→B advance 3 (kerned -3), B→C advance 7 (+3): non-uniform.
    page_text, stream = _stream_for("ABC", [3.0, 7.0, 5.0])
    words = measure_block_words(_block("ABC"), page_text, stream, metrics)
    assert words[0] is not None
    assert words[0].residual_px > 1.0


def test_unmatched_line_yields_none_measurements() -> None:
    metrics = {"f1": _metrics({"A": 600})}
    page_text, stream = _stream_for("XYZ", [5.0, 5.0, 5.0])
    words = measure_block_words(_block("AB CD"), page_text, stream, metrics)
    assert words == [None, None]


# ---- decisions --------------------------------------------------------------

def _word(text: str, size: float = 10.0) -> WordBox:
    return WordBox(text=text, x=0, width=20, baseline_y=40, font_id="f1", font_size=size)


def test_measured_uniform_word_stays_word_with_high_confidence() -> None:
    engine = AdaptiveReconstructionEngine({"f1": _metrics({"A": 600, "B": 400})})
    measurement = WordMeasurement(advance_px=14.0, tracking_px=2.0, residual_px=0.02, glyph_count=2)
    decision = engine.decide_word(_word("AB"), measurement=measurement)
    assert decision.mode == "word"
    assert decision.reason == "tracking"
    assert decision.letter_spacing == 2.0
    assert decision.reconstruction_confidence >= 0.99
    assert decision.width_error == 0.02  # post-fit residual, not a bbox gap


def test_measured_untracked_word_reason_is_none() -> None:
    engine = AdaptiveReconstructionEngine({"f1": _metrics({"A": 600, "B": 400})})
    measurement = WordMeasurement(advance_px=10.0, tracking_px=0.0, residual_px=0.01, glyph_count=2)
    decision = engine.decide_word(_word("AB"), measurement=measurement)
    assert decision.mode == "word" and decision.reason == "none"
    assert decision.letter_spacing == 0.0


def test_measured_nonuniform_word_escalates_to_glyph() -> None:
    engine = AdaptiveReconstructionEngine({"f1": _metrics({"H": 700, "T": 600})})
    measurement = WordMeasurement(advance_px=11.0, tracking_px=-1.0,
                                  residual_px=ADVANCE_RESIDUAL_TOLERANCE_PX * 4, glyph_count=2)
    decision = engine.decide_word(_word("HT"), measurement=measurement)
    assert decision.mode == "glyph"
    assert decision.letter_spacing == -1.0  # the uniform (real) part is kept


def test_no_measurement_falls_back_to_bbox_path_unchanged() -> None:
    engine = AdaptiveReconstructionEngine({"f1": _metrics({"A": 600, "B": 400})})
    word = _word("AB")
    word.width = 10.05
    decision = engine.decide_word(word)  # measurement=None → legacy path
    assert decision.mode == "word" and decision.reason == "none"
    assert decision.tolerance != ADVANCE_RESIDUAL_TOLERANCE_PX
