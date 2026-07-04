from app.pipeline.stages.extract_fonts import _sanitize_for_web
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
