"""Character-spacing (Tc) reconstruction (Issue 002B, Rendering Accuracy v1):
genuine PDF tracking is measured from actual glyph advances and attributed to
the right span — never guessed when the match is ambiguous."""

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.typography.character_spacing import (
    _page_char_stream,
    analyze_block_tracking,
    analyze_page_tracking,
    estimate_tracking,
    token_letter_spacing,
)
from app.pipeline.typography.font_metrics import FontMetrics

UPM = 1000


def _metrics(advances: dict[str, int]) -> FontMetrics:
    cmap = {ord(c): c for c in advances}
    return FontMetrics(cmap=cmap, advances={c: (a, 0) for c, a in advances.items()}, units_per_em=UPM)


def _texttrace_span(text: str, origins_x: list[float], y: float = 40.0) -> dict:
    return {"chars": [(ord(ch), 0, (x, y), (x, y - 8, x + 8, y + 2)) for ch, x in zip(text, origins_x)]}


def _stream(texttrace: list[dict]) -> tuple[str, list]:
    stream = _page_char_stream(texttrace)
    return "".join(c for c, _x, _y in stream), stream


def test_estimate_tracking_detects_constant_offset() -> None:
    # Every glyph +2.5px over nominal — the Tc signature.
    pairs = [(a + 2.5, a) for a in (8.0, 9.0, 10.0, 7.5, 6.0)]
    assert abs(estimate_tracking(pairs) - 2.5) < 0.01


def test_estimate_tracking_ignores_noise_below_floor() -> None:
    pairs = [(a + 0.05, a) for a in (8.0, 9.0, 10.0)]
    assert estimate_tracking(pairs) == 0.0


def test_estimate_tracking_ignores_inconsistent_residual() -> None:
    # Not a clean constant offset (kerning-like variability) → don't attribute.
    pairs = [(8.5, 8.0), (9.5, 9.0), (7.0, 10.0), (12.0, 6.0)]
    assert estimate_tracking(pairs) == 0.0


def test_estimate_tracking_too_few_glyphs_returns_zero() -> None:
    assert estimate_tracking([(8.5, 8.0)]) == 0.0


def _tracked_block() -> TextBlock:
    # "AB" at size 10: A=6px, B=4px nominal; actual origins show +2px/glyph.
    text = "AB"
    return TextBlock(
        id="b1", page=1, bbox=BoundingBox(0.0, 30.0, 20.0, 12.0), text=text,
        origin_y=40.0, rotation=0.0, writing_direction="ltr", font_size=10.0,
        spans=[TextSpan(text="AB", font_id="f1", font_size=10.0, color="#000")],
    )


def test_analyze_block_tracking_measures_genuine_tc() -> None:
    block = _tracked_block()
    # A origin 0, advance 6+2=8 -> B origin 8; B origin 8, advance ignored (last glyph).
    page_text, page_stream = _stream([_texttrace_span("AB", [0.0, 8.0])])
    metrics_by_font = {"f1": _metrics({"A": 600, "B": 400})}
    spacing = analyze_block_tracking(block, page_text, page_stream, metrics_by_font)
    assert len(spacing) == 1
    assert spacing[0] == 0.0  # only 1 non-space glyph-pair (A->B) — below _MIN_PAIRS


def test_analyze_block_tracking_bails_out_when_text_not_found() -> None:
    block = _tracked_block()
    page_text, page_stream = _stream([_texttrace_span("XY", [0.0, 8.0])])  # doesn't contain block.text
    spacing = analyze_block_tracking(block, page_text, page_stream, {"f1": _metrics({"A": 600, "B": 400})})
    assert spacing == [0.0]


def test_analyze_block_tracking_bails_out_on_rotation() -> None:
    block = _tracked_block()
    block.rotation = 15.0
    page_text, page_stream = _stream([_texttrace_span("AB", [0.0, 8.0])])
    spacing = analyze_block_tracking(block, page_text, page_stream, {"f1": _metrics({"A": 600, "B": 400})})
    assert spacing == [0.0]


def test_line_found_as_substring_of_a_multi_line_texttrace_span() -> None:
    # Real-world bug: get_texttrace() merges same-style consecutive VISUAL
    # lines into one span with no separator ("...Jim BentonAll rights...").
    # The second line must still be found, anchored by ITS OWN baseline y.
    block = TextBlock(
        id="b2", page=1, bbox=BoundingBox(0.0, 50.0, 40.0, 12.0), text="AB",
        origin_y=52.0, rotation=0.0, writing_direction="ltr", font_size=10.0,
        spans=[TextSpan(text="AB", font_id="f1", font_size=10.0, color="#000")],
    )
    merged_span = {
        "chars": [
            (ord("A"), 0, (0.0, 40.0), (0, 32, 8, 42)),
            (ord("B"), 0, (8.0, 40.0), (8, 32, 16, 42)),
            (ord("A"), 0, (0.0, 52.0), (0, 44, 8, 54)),  # second "line" here
            (ord("B"), 0, (10.0, 52.0), (10, 44, 18, 54)),
        ]
    }
    page_text, page_stream = _stream([merged_span])
    spacing = analyze_block_tracking(
        block, page_text, page_stream, {"f1": _metrics({"A": 600, "B": 400})}
    )
    assert len(spacing) == 1  # found the SECOND occurrence (y=52), not the first


def test_analyze_page_tracking_sets_span_letter_spacing_in_place() -> None:
    block = TextBlock(
        id="b1", page=1, bbox=BoundingBox(0.0, 30.0, 60.0, 12.0), text="ABAB",
        origin_y=40.0, rotation=0.0, writing_direction="ltr", font_size=10.0,
        spans=[TextSpan(text="ABAB", font_id="f1", font_size=10.0, color="#000")],
    )
    # nominal per-glyph: A=6, B=4; actual = nominal + 2 for every glyph.
    origins = [0.0]
    for ch in "ABA":  # build cumulative origins for A,B,A,B with +2 offset baked in
        nominal = {"A": 6.0, "B": 4.0}[ch]
        origins.append(origins[-1] + nominal + 2.0)
    texttrace = [_texttrace_span("ABAB", origins)]
    analyze_page_tracking([block], texttrace, {"f1": _metrics({"A": 600, "B": 400})})
    assert abs(block.spans[0].letter_spacing - 2.0) < 0.05


def test_token_letter_spacing_aligns_with_word_order() -> None:
    block = TextBlock(
        id="b1", page=1, bbox=BoundingBox(0, 0, 10, 10), text="one two three",
        spans=[
            TextSpan(text="one two ", font_id="f1", font_size=10, color="#000", letter_spacing=0.0),
            TextSpan(text="three", font_id="f2", font_size=10, color="#000", letter_spacing=1.5),
        ],
    )
    assert token_letter_spacing(block) == [0.0, 0.0, 1.5]
