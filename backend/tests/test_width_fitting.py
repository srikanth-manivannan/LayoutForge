"""Width fitting (ACC-2): letter_spacing computed from real font advances
so the overlay's rendered width equals the width the PDF laid the text out
at. Uses a font built with known advances, so expectations are exact."""

import io

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.stages.normalize_idm import (
    FontMetrics,
    compute_spacing,
    load_font_metrics,
    natural_text_width,
)

UPM = 1000
ADV_A = 600
ADV_B = 400


def make_metrics() -> FontMetrics:
    return FontMetrics(cmap={ord("A"): "A", ord("B"): "B"}, advances={"A": (ADV_A, 0), "B": (ADV_B, 0)}, units_per_em=UPM)


def make_block(text: str, bbox_width: float, font_size: float = 10.0, **kwargs) -> TextBlock:
    return TextBlock(
        id="b1",
        page=1,
        bbox=BoundingBox(x=0, y=0, width=bbox_width, height=12),
        text=text,
        font_id="f1",
        font_size=font_size,
        spans=[TextSpan(text=text, font_id="f1", font_size=font_size)],
        **kwargs,
    )


def test_natural_width_uses_real_advances() -> None:
    width, missing = natural_text_width("AB", 10.0, make_metrics())
    assert missing == 0
    assert width == (ADV_A + ADV_B) / UPM * 10.0  # 10.0


def test_letter_spacing_distributes_pdf_extra_width_per_char() -> None:
    # natural = 10.0; PDF laid it out at 11.0 → +1.0 over 2 chars = 0.5/char
    block = make_block("AB", bbox_width=11.0)
    assert compute_spacing(block, {"f1": make_metrics()}) == (0.5, 0.0)


def test_letter_spacing_negative_for_tightened_text() -> None:
    block = make_block("AB", bbox_width=9.0)
    assert compute_spacing(block, {"f1": make_metrics()}) == (-0.5, 0.0)


def test_justified_surplus_goes_to_word_spacing_not_letters() -> None:
    metrics = FontMetrics(
        cmap={ord("A"): "A", ord("B"): "B", ord(" "): "space"},
        advances={"A": (ADV_A, 0), "B": (ADV_B, 0), "space": (250, 0)},
        units_per_em=UPM,
    )
    # natural = (600+250+400)/1000*10 = 12.5; bbox 14.5 → the 2.0 surplus
    # lands on the single space — word interiors stay untouched, matching
    # how justified PDF text carries its surplus (Tw).
    block = make_block("A B", bbox_width=14.5)
    assert compute_spacing(block, {"f1": metrics}) == (0.0, 2.0)


def test_spacing_skips_rotated_rtl_and_unmeasurable() -> None:
    metrics = {"f1": make_metrics()}
    assert compute_spacing(make_block("AB", 11.0, rotation=90.0), metrics) is None
    assert compute_spacing(make_block("AB", 11.0, writing_direction="rtl"), metrics) is None
    assert compute_spacing(make_block("AB", 11.0), {"f1": None}) is None


def test_spacing_skips_implausible_corrections() -> None:
    # +10 over 2 chars = 5/char = 50% of font size — beyond the 25% guard.
    assert compute_spacing(make_block("AB", 20.0), {"f1": make_metrics()}) is None


def test_spacing_skips_low_glyph_coverage() -> None:
    # "AXYZ": 3 of 4 chars missing from the font → unreliable, skip.
    block = make_block("AXYZ", 30.0)
    assert compute_spacing(block, {"f1": make_metrics()}) is None


def test_load_font_metrics_from_real_file(tmp_path) -> None:
    pen = T2CharStringPen(ADV_A, None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 700))
    pen.lineTo((500, 700))
    pen.closePath()
    builder = FontBuilder(UPM, isTTF=False)
    builder.setupGlyphOrder([".notdef", "A"])
    builder.setupCharacterMap({ord("A"): "A"})
    builder.setupCFF("T", {}, {"A": pen.getCharString(), ".notdef": T2CharStringPen(500, None).getCharString()}, {})
    builder.setupHorizontalMetrics({".notdef": (500, 0), "A": (ADV_A, 0)})
    builder.setupHorizontalHeader(ascent=700, descent=0)
    builder.setupNameTable({"familyName": "T", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    path = tmp_path / "t.otf"
    builder.save(str(path))

    metrics = load_font_metrics(path)
    assert metrics is not None
    assert metrics.cmap[ord("A")] == "A"
    assert metrics.advances["A"][0] == ADV_A
    assert metrics.units_per_em == UPM
