"""Run.rise extraction (approved 2026-07-12): baseline rise measured from
texttrace glyph y-origins, carried as data to the renderer — never inferred
by it. Field-proven case: `the` raised 10.86px inside `Tot the Toad`."""

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.typography.character_spacing import _page_char_stream, measure_span_rises
from app.pipeline.typography.run_builder import build_runs


def _stream(chars: list[tuple[str, float, float]]):
    trace = [{"chars": [(ord(c), 0, (x, y), (x, y - 8, x + 8, y + 2)) for c, x, y in chars]}]
    stream = _page_char_stream(trace)
    return "".join(c for c, _x, _y in stream), stream


def _block(text: str, spans: list[TextSpan], origin_y: float = 134.15, size: float = 115.0) -> TextBlock:
    return TextBlock(
        id="b1", page=1, bbox=BoundingBox(140, 30, 330, 125), text=text,
        origin_y=origin_y, rotation=0.0, writing_direction="ltr", font_size=size, spans=spans,
    )


def test_raised_span_rise_is_measured() -> None:
    # "Tot the Toad" pattern: Tot/Toad on y=134.15, the RAISED at y=123.29.
    chars = [("T", 146.0, 134.15), ("o", 188.0, 134.15), ("t", 226.0, 134.15),
             (" ", 265.0, 134.15),
             ("t", 268.6, 123.29), ("h", 288.8, 123.29), ("e", 312.3, 123.29),
             ("T", 333.5, 134.15), ("o", 375.5, 134.15)]
    page_text, stream = _stream(chars)
    # NB: like the real PDF, there is NO space between "the" and "To" — the
    # visual gap is glyph-metric. block.text must equal the stream text.
    block = _block("Tot theTo", [
        TextSpan(text="Tot ", font_id="f1", font_size=115.0, color="#fff"),
        TextSpan(text="the", font_id="f1", font_size=60.5, color="#fff"),
        TextSpan(text="To", font_id="f1", font_size=115.0, color="#fff"),
    ])
    rises = measure_span_rises(block, page_text, stream)
    assert rises[0] == 0.0                    # Tot: on the main baseline
    assert abs(rises[1] - 10.86) < 0.01       # the: raised (positive = up)
    assert rises[2] == 0.0                    # Toad: back on baseline


def test_subpixel_offsets_are_noise_not_rise() -> None:
    chars = [("A", 0.0, 100.2), ("B", 10.0, 100.2)]
    page_text, stream = _stream(chars)
    block = _block("AB", [TextSpan(text="AB", font_id="f1", font_size=12.0, color="#000")], origin_y=100.0, size=12.0)
    assert measure_span_rises(block, page_text, stream) == [0.0]


def test_unmatched_line_yields_zero_rises() -> None:
    page_text, stream = _stream([("X", 0.0, 50.0)])
    block = _block("AB", [TextSpan(text="AB", font_id="f1", font_size=12.0, color="#000")])
    assert measure_span_rises(block, page_text, stream) == [0.0]


def test_run_builder_never_merges_across_rise_and_propagates_it() -> None:
    fonts = {"f1": FontResource(id="f1", original_name="KGDancing", family="KGDancing")}
    # Same font/size/color — only rise differs: MUST stay separate runs.
    block = _block("abcdef", [
        TextSpan(text="abc", font_id="f1", font_size=60.0, color="#fff", rise=0.0),
        TextSpan(text="def", font_id="f1", font_size=60.0, color="#fff", rise=10.86),
    ])
    runs = build_runs(block, fonts)
    assert [r.text for r in runs] == ["abc", "def"]
    assert runs[0].rise == 0.0 and runs[1].rise == 10.86


def test_space_variant_mismatch_still_matches() -> None:
    """Field regression: extraction reported U+200A where texttrace reported
    U+0020 — the line silently failed to match, zeroing rise/Tc/measurement
    for exactly the display line that needed them. Matching must fold
    Unicode space variants on both sides."""
    chars = [("T", 146.0, 134.15), ("o", 188.0, 134.15), ("t", 226.0, 134.15),
             (" ", 265.0, 134.15),  # texttrace: plain U+0020
             ("t", 268.6, 123.29), ("h", 288.8, 123.29), ("e", 312.3, 123.29)]
    page_text, stream = _stream(chars)
    block = _block("Tot the", [  # extraction: U+200A hair space (explicit escape)
        TextSpan(text="Tot ", font_id="f1", font_size=115.0, color="#fff"),
        TextSpan(text="the", font_id="f1", font_size=60.5, color="#fff"),
    ])
    rises = measure_span_rises(block, page_text, stream)
    assert rises[0] == 0.0
    assert abs(rises[1] - 10.86) < 0.01


def test_span_rise_survives_serialization() -> None:
    span = TextSpan(text="the", font_id="f1", font_size=60.0, color="#fff", rise=10.86)
    assert TextSpan.from_dict(span.to_dict()).rise == 10.86
    assert TextSpan.from_dict({"text": "old", "font_id": None, "font_size": 1.0, "color": "#000"}).rise == 0.0
