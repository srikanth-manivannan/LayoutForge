"""Character Fidelity (the primary Quality Gate criterion): no character may
be silently lost. Covers the live regression (a no-post/no-cmap subset
crashed the sanitizer and was silently dropped, resurrecting invisible
characters) and the structural guarantee (blank mappings are purged so
browsers fall back visibly)."""

import io
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from app.pipeline.elements.font import FontResource
from app.pipeline.elements.textbox import WordBox
from app.pipeline.stages.extract_fonts import _purge_blank_mappings, _sanitize_for_web
from app.pipeline.typography.adaptive_reconstruction import AdaptiveReconstructionEngine
from app.pipeline.typography.font_metrics import FontMetrics
from tests.conftest import make_minimal_ttf_bytes

UPM = 1000


def _box():
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    pen.lineTo((50, 700))
    pen.lineTo((550, 700))
    pen.lineTo((550, 0))
    pen.closePath()
    return pen.glyph()


def _blank():
    return TTGlyphPen(None).glyph()


def test_sanitize_survives_subset_missing_post_AND_cmap() -> None:
    """The exact live regression: fontTools raises 'illegal use of
    getGlyphOrder()' for a subset with neither post nor cmap; the sanitizer
    swallowed it and dropped the font — the sibling merge then had no donor
    and characters painted blank. Sanitize must repair, not drop."""
    font = TTFont(io.BytesIO(make_minimal_ttf_bytes()))
    for table in ("post", "cmap"):
        if table in font:
            del font[table]
    stripped = io.BytesIO()
    font.save(stripped)

    sanitized = _sanitize_for_web("ttf", stripped.getvalue(), family="NoPostNoCmap")

    assert sanitized is not None, "a repairable subset must never be dropped"
    repaired = TTFont(io.BytesIO(sanitized))
    assert "cmap" in repaired and "post" in repaired


def test_purge_unmaps_blank_glyphs_but_keeps_whitespace_and_real(tmp_path: Path) -> None:
    """A cmap entry pointing at an empty non-whitespace glyph paints as
    NOTHING (browsers only fall back on missing entries, not blank ones).
    The purge unmaps it — the char then renders via the fallback stack."""
    order = [".notdef", "space", "A", "g"]
    builder = FontBuilder(UPM, isTTF=True)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap({0x20: "space", ord("A"): "A", ord("g"): "g"})
    builder.setupGlyf({".notdef": _blank(), "space": _blank(), "A": _box(), "g": _blank()})
    builder.setupHorizontalMetrics({g: (600, 50) for g in order})
    builder.setupHorizontalHeader(ascent=700, descent=0)
    builder.setupNameTable({"familyName": "PurgeTest", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    filename = "purge-test.ttf"
    builder.save(str(tmp_path / filename))

    resource = FontResource(id="f-p", original_name="XXXXXX+PurgeTest", family="PurgeTest", filename=filename)
    purged = _purge_blank_mappings(tmp_path, [resource])

    assert purged == {"f-p": 1}  # only 'g' (blank, non-whitespace)
    result = TTFont(io.BytesIO((tmp_path / filename).read_bytes()))
    cmap = result.getBestCmap()
    assert ord("g") not in cmap, "blank mapping must be unmapped → browser fallback"
    assert cmap[ord("A")] == "A", "real glyphs stay"
    assert cmap[0x20] == "space", "whitespace legitimately blank — stays"


def test_profile_counts_substituted_characters() -> None:
    """Post-purge, a char absent from the cmap is a SUBSTITUTION (visible in
    fallback), counted in the profile; chars_lost is 0 by construction."""
    metrics = FontMetrics(cmap={ord("A"): "A"}, advances={"A": (600, 0)}, units_per_em=UPM)
    engine = AdaptiveReconstructionEngine({"f1": metrics})
    # "Ag" → 'A' renders in-font, 'g' was purged → substituted
    word = WordBox(text="Ag", x=0.0, width=12.0, baseline_y=0.0, font_id="f1", font_size=10.0)
    engine.reconstruct_word(word)

    profile = engine.profile.to_dict()
    assert profile["chars_total"] == 2
    assert profile["chars_substituted"] == 1
    assert profile["chars_lost"] == 0
    assert profile["character_substitution_rate"] == 0.5
