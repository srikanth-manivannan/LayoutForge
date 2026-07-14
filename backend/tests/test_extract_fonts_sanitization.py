import io
from collections import Counter
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from app.pipeline.elements.font import FontResource
from app.pipeline.stages.extract_fonts import _reconcile_cmap_from_usage, _sanitize_for_web
from tests.conftest import make_minimal_ttf_bytes


def test_sanitize_for_web_accepts_valid_ttf_and_returns_parseable_bytes() -> None:
    original = make_minimal_ttf_bytes()

    sanitized = _sanitize_for_web("ttf", original)

    assert sanitized is not None
    # The whole point: the resaved bytes must themselves be loadable by a
    # strict parser (a stand-in for the browser's OTS sanitizer), proving
    # this isn't just an echo of the input.
    from fontTools.ttLib import TTFont

    TTFont(__import__("io").BytesIO(sanitized))


def test_sanitize_for_web_rejects_non_web_formats() -> None:
    # "cff" is a bare CFF table, not a standalone font file — browsers
    # cannot load it via @font-face regardless of content validity.
    assert _sanitize_for_web("cff", make_minimal_ttf_bytes()) is None
    assert _sanitize_for_web("pfb", b"irrelevant") is None


def test_sanitize_for_web_handles_corrupt_font_gracefully() -> None:
    assert _sanitize_for_web("ttf", b"this is not a font") is None


def _make_two_glyph_ttf_bytes() -> bytes:
    """A font with TWO distinctly-named glyphs ("s" and "s.salt", a
    stylistic-alternate naming convention) but only glyph "s" registered in
    the initial cmap — mirrors a subset where a codepoint's canonical cmap
    entry hasn't yet been reconciled against actual PDF usage."""
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 500))
    pen.lineTo((500, 500))
    pen.lineTo((500, 0))
    pen.closePath()
    glyph = pen.glyph()

    builder = FontBuilder(unitsPerEm=1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "s", "s.salt"])
    builder.setupCharacterMap({ord("s"): "s"})
    builder.setupGlyf({".notdef": glyph, "s": glyph, "s.salt": glyph})
    builder.setupHorizontalMetrics({".notdef": (500, 0), "s": (500, 0), "s.salt": (300, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()

    buffer = io.BytesIO()
    builder.save(buffer)
    return buffer.getvalue()


def test_reconcile_cmap_picks_the_majority_glyph_not_the_last_seen(tmp_path: Path) -> None:
    """Issue 005 (2026-07-14): a real book used TWO different glyphs for
    the letter 's' within one word — a deliberate InDesign stylistic-
    alternate substitution on some occurrences, not all. A cmap can only
    hold one glyph per codepoint; usage must be resolved by MAJORITY vote,
    never by "whichever occurrence happened to be processed last" (a plain
    dict-assignment loop is order-dependent and silently picks the wrong
    glyph as often as the right one)."""
    fonts_dir = tmp_path
    filename = "test.ttf"
    (fonts_dir / filename).write_bytes(_make_two_glyph_ttf_bytes())
    font = FontResource(id="f1", original_name="Test", family="Test", filename=filename)

    # gid 1 ("s", standard) seen twice; gid 2 ("s.salt", alternate) once —
    # majority is gid 1, even though gid 2 is added to the Counter LAST.
    usage = {ord("s"): Counter({1: 2, 2: 1})}

    _reconcile_cmap_from_usage(fonts_dir, font, usage)

    result = TTFont(io.BytesIO((fonts_dir / filename).read_bytes()))
    cmap = result.getBestCmap()
    assert cmap[ord("s")] == "s"  # majority glyph, not the alternate


def test_reconcile_cmap_picks_the_alternate_when_it_is_the_majority(tmp_path: Path) -> None:
    """Symmetric case: if the alternate glyph is genuinely used MORE often
    for a codepoint, it should win — this is majority-vote, not a hardcoded
    preference for the base glyph name."""
    fonts_dir = tmp_path
    filename = "test.ttf"
    (fonts_dir / filename).write_bytes(_make_two_glyph_ttf_bytes())
    font = FontResource(id="f1", original_name="Test", family="Test", filename=filename)

    usage = {ord("s"): Counter({1: 1, 2: 3})}

    _reconcile_cmap_from_usage(fonts_dir, font, usage)

    result = TTFont(io.BytesIO((fonts_dir / filename).read_bytes()))
    cmap = result.getBestCmap()
    assert cmap[ord("s")] == "s.salt"


def test_sanitize_synthesizes_missing_required_tables() -> None:
    """PDF subsets often omit tables browsers require (OTS rejects the
    whole file over a missing OS/2 — seen live with PrinceXML subsets).
    Sanitization must repair, not just re-save."""
    import io

    from fontTools.ttLib import TTFont

    original = make_minimal_ttf_bytes()
    font = TTFont(io.BytesIO(original))
    if "OS/2" in font:
        del font["OS/2"]
    if "post" in font:
        del font["post"]
    stripped = io.BytesIO()
    font.save(stripped)

    sanitized = _sanitize_for_web("ttf", stripped.getvalue(), family="RepairMe")

    assert sanitized is not None
    repaired = TTFont(io.BytesIO(sanitized))
    for required in ("OS/2", "post", "cmap", "name"):
        assert required in repaired, f"missing {required}"
    # OS/2 metrics agree with hhea (baseline-consistency rule).
    assert repaired["OS/2"].sTypoAscender == repaired["hhea"].ascent
