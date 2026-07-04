"""Engine stabilization (M1.7): regression tests that pin the Adaptive
Reconstruction Engine's behavior and the conversion report so future work
can't silently regress accuracy, the reconstruction profile, memory, or
speed. The committed synthetic corpus (make_rich_pdf_bytes) stands in for
the real benchmark corpus, which plugs into the same harness.

Quality Gate (docs/design/QUALITY_GATE.md) checks:
- zero UNEXPECTED font fallbacks
- reconstruction profile populated + sane
- glyph fraction bounded (adaptive precision holds)
- performance within a generous budget on many pages
"""

import time
from pathlib import Path

from app.pipeline.stages.extract_fonts import ExtractFontsStage
from app.pipeline.stages.extract_images import ExtractImagesStage
from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.render_backgrounds import RenderBackgroundsStage
from app.services.conversion_report import build_report
from tests.conftest import make_rich_pdf_bytes
from tests.test_extraction import make_context_with_metadata


def _run_pipeline(context, storage) -> None:
    RenderBackgroundsStage(storage, dpi=72).run(context)
    ExtractFontsStage(storage).run(context)
    ExtractImagesStage(storage).run(context)
    ExtractTextStage().run(context)
    NormalizeIdmStage(storage).run(context)  # storage → metrics → adaptive reconstruction


def test_benchmark_profile_is_populated_and_sane(db_session, tmp_path: Path) -> None:
    pdf = tmp_path / "bench.pdf"
    pdf.write_bytes(make_rich_pdf_bytes(pages=3))
    context, storage, _, _ = make_context_with_metadata(db_session, tmp_path, pdf)
    _run_pipeline(context, storage)

    profile = context.document.reconstruction_profile
    assert profile["words"] > 0
    # Adaptive precision must hold: the cheap WORD level dominates.
    assert 0.0 <= profile["glyph_fraction"] <= 0.6
    assert profile["by_mode"].get("word", 0) >= profile["by_mode"].get("glyph", 0)
    # Confidence is an internal metric, but a healthy doc should be high.
    assert profile["mean_reconstruction_confidence"] >= 0.75


def test_no_unexpected_font_fallbacks(db_session, tmp_path: Path) -> None:
    """Quality Gate: every EMBEDDED font a page uses must have produced a
    web-loadable file. (Non-embedded base-14 fonts are expected fallbacks,
    handled by metric-compatible local stacks — not counted here.)"""
    pdf = tmp_path / "fonts.pdf"
    pdf.write_bytes(make_rich_pdf_bytes(pages=2))
    context, storage, _, _ = make_context_with_metadata(db_session, tmp_path, pdf)
    _run_pipeline(context, storage)

    for font in context.document.fonts:
        # Embedded fonts (the synthetic corpus embeds its fonts) must have a
        # served file — a missing one is an UNEXPECTED fallback.
        if font.embedded:
            assert font.filename, f"embedded font {font.original_name} produced no web file"


def test_words_are_pinned_and_carry_decisions(db_session, tmp_path: Path) -> None:
    pdf = tmp_path / "pin.pdf"
    pdf.write_bytes(make_rich_pdf_bytes(pages=1))
    context, storage, _, _ = make_context_with_metadata(db_session, tmp_path, pdf)
    _run_pipeline(context, storage)

    words = [w for block in context.document.pages[0].text_blocks for w in block.words]
    assert words, "expected word-pinned lines"
    for w in words:
        assert w.mode in ("word", "glyph")
        assert 0.0 <= w.reconstruction_confidence <= 1.0


def test_performance_budget_many_pages(db_session, tmp_path: Path) -> None:
    """Generous wall-clock ceiling so this catches order-of-magnitude
    regressions (e.g. an accidental O(n^2)) without being flaky. 12 pages of
    dense text must reconstruct well under the budget."""
    pdf = tmp_path / "perf.pdf"
    pdf.write_bytes(make_rich_pdf_bytes(pages=12))
    context, storage, _, _ = make_context_with_metadata(db_session, tmp_path, pdf)
    RenderBackgroundsStage(storage, dpi=72).run(context)
    ExtractFontsStage(storage).run(context)
    ExtractImagesStage(storage).run(context)
    ExtractTextStage().run(context)

    started = time.perf_counter()
    NormalizeIdmStage(storage).run(context)
    elapsed = time.perf_counter() - started

    words = context.document.reconstruction_profile["words"]
    assert words > 0
    # Reconstruction (the M1.x work) for a dozen pages must stay well under a
    # generous ceiling; real budget tracking lives in report.json.
    assert elapsed < 5.0, f"reconstruction took {elapsed:.2f}s for {words} words"


def test_conversion_report_shape(db_session, tmp_path: Path) -> None:
    from app.pipeline.engine import StageMetric

    pdf = tmp_path / "rep.pdf"
    pdf.write_bytes(make_rich_pdf_bytes(pages=2))
    context, storage, _, _ = make_context_with_metadata(db_session, tmp_path, pdf)
    _run_pipeline(context, storage)

    metrics = [StageMetric("normalize_idm", 0.5, 12.3), StageMetric("generate_html", 0.2, 4.0)]
    report = build_report(context.document, metrics)

    assert report["report_version"] == 1
    assert report["pages"] == 2
    assert "reconstruction_profile" in report
    assert report["accuracy"]["mean_reconstruction_confidence"] >= 0.0
    assert report["performance"]["total_duration_seconds"] == 0.7
    assert report["performance"]["peak_memory_mb"] == 12.3
    assert len(report["performance"]["stages"]) == 2
