import io

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont

from app.pipeline.stages.extract_fonts import _wrap_bare_cff

ADVANCE_A = 600


def make_bare_cff_bytes() -> bytes:
    """A bare CFF font program (what PyMuPDF returns for ext='cff'): build a
    minimal OTF with one real glyph, then compile just its 'CFF ' table —
    exactly the payload a PDF embeds for a Type1C font."""
    glyphs = {}
    pen = T2CharStringPen(ADVANCE_A, None)
    pen.moveTo((50, 0))
    pen.lineTo((50, 700))
    pen.lineTo((550, 700))
    pen.lineTo((550, 0))
    pen.closePath()
    glyphs["A"] = pen.getCharString()
    notdef_pen = T2CharStringPen(500, None)
    glyphs[".notdef"] = notdef_pen.getCharString()

    builder = FontBuilder(1000, isTTF=False)
    builder.setupGlyphOrder([".notdef", "A"])
    builder.setupCharacterMap({ord("A"): "A"})
    builder.setupCFF("TestCFF", {}, glyphs, {})
    builder.setupHorizontalMetrics({".notdef": (500, 0), "A": (ADVANCE_A, 50)})
    builder.setupHorizontalHeader(ascent=700, descent=0)
    builder.setupNameTable({"familyName": "TestCFF", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()

    otf = builder.font
    return otf["CFF "].compile(otf)


def test_wrap_bare_cff_produces_browser_loadable_otf() -> None:
    wrapped = _wrap_bare_cff(make_bare_cff_bytes(), family="TestCFF")

    assert wrapped is not None
    # Must survive a strict re-parse (stand-in for the browser's OTS).
    font = TTFont(io.BytesIO(wrapped))
    assert font.sfntVersion == "OTTO"
    for required in ("CFF ", "cmap", "hmtx", "head", "hhea", "maxp", "name", "OS/2", "post"):
        assert required in font, f"missing {required}"


def test_wrap_bare_cff_recovers_cmap_and_advance_widths() -> None:
    wrapped = _wrap_bare_cff(make_bare_cff_bytes(), family="TestCFF")
    assert wrapped is not None
    font = TTFont(io.BytesIO(wrapped))

    # cmap recovered from AGL glyph names — text using this font maps again.
    assert font.getBestCmap().get(ord("A")) == "A"
    # Advance width preserved — this is what makes overlay text line up
    # with the rasterized background instead of rendering doubled.
    advance, _lsb = font["hmtx"]["A"]
    assert advance == ADVANCE_A


def test_wrap_bare_cff_line_metrics_match_mupdf() -> None:
    """The accuracy contract behind baseline placement: NormalizeIdmStage
    derives line_height from MuPDF's ascender/descender, and the browser
    derives the baseline from the font file's metric tables — the overlay
    only lands on the rasterized background when both use the same numbers
    (page-26 regression: bounds-derived metrics painted the title ~4.6pt
    high)."""
    import fitz

    bare = make_bare_cff_bytes()
    wrapped = _wrap_bare_cff(bare, family="TestCFF")
    assert wrapped is not None

    mupdf = fitz.Font(fontbuffer=bare)
    font = TTFont(io.BytesIO(wrapped))
    upm = font["head"].unitsPerEm
    expected_ascent = round(mupdf.ascender * upm)
    expected_descent = round(mupdf.descender * upm)

    assert font["hhea"].ascent == expected_ascent
    assert font["hhea"].descent == expected_descent
    assert font["OS/2"].sTypoAscender == expected_ascent
    assert font["OS/2"].sTypoDescender == expected_descent
    assert font["OS/2"].usWinAscent == max(expected_ascent, 0)
    assert font["OS/2"].usWinDescent == abs(min(expected_descent, 0))


def test_wrap_bare_cff_handles_garbage_gracefully() -> None:
    assert _wrap_bare_cff(b"this is not a font program", family="Junk") is None
