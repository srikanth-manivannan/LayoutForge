"""Sibling-subset completion: two TrueType subsets of the same base font
partition their outlines (each keeps empty placeholders for the other's
glyphs — exactly what dropped 'j'/'g' from the reference book's page 5).
After _complete_sibling_subsets both files must render every glyph."""

import io
import uuid
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from app.pipeline.elements.font import FontResource
from app.pipeline.stages.extract_fonts import _complete_sibling_subsets

UPM = 1000
GLYPH_ORDER = [".notdef", "A", "B"]


def _box_glyph(width: int):
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    pen.lineTo((50, 700))
    pen.lineTo((width - 50, 700))
    pen.lineTo((width - 50, 0))
    pen.closePath()
    return pen.glyph()


def _empty_glyph():
    return TTGlyphPen(None).glyph()


def _make_subset(tmp_path: Path, name: str, real: set[str], cmap: dict[int, str] | None) -> str:
    """A 3-glyph TTF where only `real` glyph names have outlines."""
    builder = FontBuilder(UPM, isTTF=True)
    builder.setupGlyphOrder(list(GLYPH_ORDER))
    builder.setupCharacterMap(cmap or {})
    glyphs = {g: (_box_glyph(600) if g in real else _empty_glyph()) for g in GLYPH_ORDER}
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({g: (600, 50) for g in GLYPH_ORDER})
    builder.setupHorizontalHeader(ascent=700, descent=0)
    builder.setupNameTable({"familyName": "MergeTest", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    filename = f"{name}-{uuid.uuid4().hex[:6]}.ttf"
    builder.save(str(tmp_path / filename))
    if cmap is None:
        # Simulate a PDF subset with NO cmap at all (they exist in the wild:
        # the PDF maps chars via its own encoding).
        font = TTFont(str(tmp_path / filename))
        del font["cmap"]
        font.save(str(tmp_path / filename))
    return filename


def _contours(path: Path, char: str) -> int | None:
    font = TTFont(io.BytesIO(path.read_bytes()))
    cmap = font.getBestCmap()
    glyph_name = cmap.get(ord(char))
    if glyph_name is None:
        return None
    glyph = font["glyf"][glyph_name]
    return glyph.numberOfContours


def test_partitioned_subsets_are_completed_bidirectionally(tmp_path: Path) -> None:
    # Subset 1: real 'A', empty 'B', cmap covers both (like EJSEFK).
    file_a = _make_subset(tmp_path, "a", real={"A"}, cmap={ord("A"): "A", ord("B"): "B"})
    # Subset 2: real 'B', empty 'A', NO cmap (like IPQCJC).
    file_b = _make_subset(tmp_path, "b", real={"B"}, cmap=None)

    fonts = [
        FontResource(id="f-a", original_name="AAAAAA+MergeTest", family="MergeTest", filename=file_a),
        FontResource(id="f-b", original_name="BBBBBB+MergeTest", family="MergeTest", filename=file_b),
    ]

    _complete_sibling_subsets(tmp_path, fonts)

    # Subset 1 gained B's outline; subset 2 gained a cmap AND A's outline.
    assert _contours(tmp_path / file_a, "A") == 1
    assert _contours(tmp_path / file_a, "B") == 1
    assert _contours(tmp_path / file_b, "A") == 1
    assert _contours(tmp_path / file_b, "B") == 1


def test_merge_skips_fonts_that_are_not_the_same_base(tmp_path: Path) -> None:
    file_a = _make_subset(tmp_path, "a", real={"A"}, cmap={ord("A"): "A"})

    # A different-glyph-count "sibling": build with an extra glyph.
    builder = FontBuilder(UPM, isTTF=True)
    order = [".notdef", "A", "B", "C"]
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap({ord("C"): "C"})
    builder.setupGlyf({g: _empty_glyph() for g in order})
    builder.setupHorizontalMetrics({g: (600, 0) for g in order})
    builder.setupHorizontalHeader(ascent=700, descent=0)
    builder.setupNameTable({"familyName": "MergeTest", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    file_b = "other.ttf"
    builder.save(str(tmp_path / file_b))
    before = (tmp_path / file_a).read_bytes()

    fonts = [
        FontResource(id="f-a", original_name="AAAAAA+MergeTest", family="MergeTest", filename=file_a),
        FontResource(id="f-b", original_name="BBBBBB+MergeTest", family="MergeTest", filename=file_b),
    ]
    _complete_sibling_subsets(tmp_path, fonts)

    # Nothing merged, nothing corrupted.
    assert (tmp_path / file_a).read_bytes() == before
