"""Phase 1 of the parallel Rich-IDM migration (ADR-011): the tree nodes
exist alongside the legacy TextBlock model and round-trip through
to_dict/from_dict, and legacy idm.json (no `regions`) still loads."""

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.glyph import Glyph
from app.pipeline.elements.line import Line
from app.pipeline.elements.page import Page
from app.pipeline.elements.paragraph import Paragraph
from app.pipeline.elements.region import Region
from app.pipeline.elements.run import Run
from app.pipeline.elements.word import Word, WordFragment


def _sample_region() -> Region:
    bbox = BoundingBox(x=10.0, y=20.0, width=300.0, height=40.0)
    glyph = Glyph(unicode="T", gid=42, cid=42, advance=12.3, dx=0.0, dy=0.0, cluster=0, bbox=bbox)
    run = Run(
        id="run-1",
        bbox=bbox,
        text="New York Times",
        font_id="f1",
        font_size=20.58,
        color="#231f20",
        italic=True,
        glyphs=[glyph],
        actual_width=280.0,
        expected_width=278.5,
    )
    # A lexical word lives on the Line and references runs by fragment (Phase 2.6).
    word = Word(id="w-1", text="Times", bbox=bbox, baseline_y=40.0, fragments=[WordFragment("run-1", "Times")])
    line = Line(id="line-1", bbox=bbox, baseline_y=40.0, ascent=16.0, descent=-4.0, line_index=0, runs=[run], words=[word])
    paragraph = Paragraph(
        id="par-1", bbox=bbox, role="p", alignment="left", line_height=31.38, word_spacing=0.0, lines=[line]
    )
    return Region(id="reg-1", bbox=bbox, kind="body", reading_order=0, paragraphs=[paragraph])


def test_region_tree_round_trips() -> None:
    region = _sample_region()
    restored = Region.from_dict(region.to_dict())
    assert restored.to_dict() == region.to_dict()
    # Spot-check the leaves survived the trip with identity intact.
    line = restored.paragraphs[0].lines[0]
    assert line.runs[0].text == "New York Times"
    assert line.runs[0].italic is True
    assert line.runs[0].glyphs[0].unicode == "T"
    assert line.words[0].text == "Times"
    assert line.words[0].fragments[0].run_id == "run-1"


def test_run_style_key_merges_identical_and_splits_on_change() -> None:
    base = dict(bbox=BoundingBox(0, 0, 1, 1), text="x", font_id="f1", font_size=20.58, color="#000000")
    a = Run(id="a", **base)
    b = Run(id="b", **base)  # identical style, different id/text position
    assert a.style_key() == b.style_key()  # → Run Builder must merge these

    bold = Run(id="c", **{**base, "weight": 700})
    italic = Run(id="d", **{**base, "italic": True})
    assert a.style_key() != bold.style_key()  # genuine style change → separate span
    assert a.style_key() != italic.style_key()


def test_font_size_noise_does_not_split_runs() -> None:
    bbox = BoundingBox(0, 0, 1, 1)
    a = Run(id="a", bbox=bbox, text="x", font_id="f1", font_size=20.580000001, color="#000")
    b = Run(id="b", bbox=bbox, text="y", font_id="f1", font_size=20.579999999, color="#000")
    assert a.style_key() == b.style_key()


def test_page_round_trips_with_regions() -> None:
    page = Page(number=1, width=648.0, height=648.0, regions=[_sample_region()])
    restored = Page.from_dict(page.to_dict())
    assert restored.to_dict() == page.to_dict()
    assert restored.regions[0].paragraphs[0].lines[0].runs[0].text == "New York Times"


def test_legacy_page_dict_without_regions_still_loads() -> None:
    """Backward compatibility: an idm.json written before Phase 1 has no
    `regions` key. It must load with an empty tree, never raise."""
    legacy = {
        "number": 1,
        "width": 648.0,
        "height": 648.0,
        "rotation": 0,
        "crop_box": None,
        "media_box": None,
        "background_image": None,
        "text_blocks": [],
        "images": [],
        "shapes": [],
        "fonts_used": [],
        # no "regions" key at all
    }
    page = Page.from_dict(legacy)
    assert page.regions == []
