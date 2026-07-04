"""Golden Corpus regression harness. Discovers any PDFs present under
`golden-corpus/<category>/`, converts each through the frozen pipeline, and
asserts its recorded baseline (manifest.json) still holds. An empty corpus
is SKIPPED, not a failure — so the structure ships now and fills over time
(see golden-corpus/README.md). This is the release-over-release quality gate
for the whole engine.
"""

import json
from pathlib import Path

import pytest

from app.pipeline.stages.extract_fonts import ExtractFontsStage
from app.pipeline.stages.extract_images import ExtractImagesStage
from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.render_backgrounds import RenderBackgroundsStage
from app.services.conversion_report import build_report

CORPUS_ROOT = Path(__file__).resolve().parents[2] / "golden-corpus"


def _discover() -> list[tuple[str, Path]]:
    if not CORPUS_ROOT.exists():
        return []
    found: list[tuple[str, Path]] = []
    for category in sorted(CORPUS_ROOT.iterdir()):
        if category.is_dir():
            for pdf in sorted(category.glob("*.pdf")):
                found.append((category.name, pdf))
    return found


CORPUS = _discover()


def test_corpus_structure_and_manifest_present() -> None:
    """The corpus scaffold must exist and be well-formed even when empty."""
    assert CORPUS_ROOT.exists(), "golden-corpus/ is missing"
    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert "categories" in manifest and len(manifest["categories"]) >= 12


@pytest.mark.skipif(not CORPUS, reason="Golden Corpus is empty — drop PDFs into golden-corpus/<category>/")
@pytest.mark.parametrize("category,pdf_path", CORPUS, ids=[f"{c}/{p.name}" for c, p in CORPUS])
def test_golden_corpus_document(category: str, pdf_path: Path, db_session, tmp_path: Path) -> None:
    from tests.test_extraction import make_context_with_metadata

    context, storage, _, _ = make_context_with_metadata(db_session, tmp_path, pdf_path, project_id=f"gc-{pdf_path.stem}")
    RenderBackgroundsStage(storage, dpi=72).run(context)
    ExtractFontsStage(storage).run(context)
    ExtractImagesStage(storage).run(context)
    ExtractTextStage().run(context)
    NormalizeIdmStage(storage).run(context)

    report = build_report(context.document, [])
    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    baseline = manifest["categories"].get(category, {}).get("files", {}).get(pdf_path.name, {})

    # Quality Gate invariants that hold for every document, baseline or not.
    for font in context.document.fonts:
        if font.embedded:
            assert font.filename, f"{pdf_path.name}: embedded font {font.original_name} produced no web file"

    # Recorded baselines (when present) must still hold.
    if "glyph_fraction_max" in baseline:
        assert report["accuracy"]["glyph_fraction"] <= baseline["glyph_fraction_max"]
    if "mean_reconstruction_confidence_min" in baseline:
        assert report["accuracy"]["mean_reconstruction_confidence"] >= baseline["mean_reconstruction_confidence_min"]
