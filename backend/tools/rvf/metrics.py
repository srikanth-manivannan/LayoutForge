"""Per-document metrics (RVF): fidelity, structure, rendering, performance.
Reads only the Document + the rendered output dirs — renderer-agnostic."""

from html.parser import HTMLParser
from pathlib import Path
from unicodedata import normalize

from app.pipeline.quality.fidelity import compute_document_fidelity
from tools.rvf.pipeline import RunArtifacts


class _TextExtractor(HTMLParser):
    """Extracts visible text only — <style>/<script> contents are NOT
    document text (inlined CSS would otherwise pollute the comparison)."""

    _SKIP = {"style", "script", "title"}  # head metadata, not document text

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.chunks.append(data)


def html_text(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    return "".join(extractor.chunks)


def nonspace(text: str) -> str:
    return "".join(normalize("NFC", text).split())


def _read(dir_path: Path, pattern: str) -> list[str]:
    if not dir_path.exists():
        return []
    return [p.read_text(encoding="utf-8") for p in sorted(dir_path.glob(pattern))]


def collect(art: RunArtifacts) -> dict:
    doc = art.document
    regions = paragraphs = lines = runs = 0
    low_conf_paras = 0
    if doc is not None:
        for page in doc.pages:
            for region in page.regions:
                regions += 1
                for paragraph in region.paragraphs:
                    paragraphs += 1
                    if paragraph.confidence < 0.6:
                        low_conf_paras += 1
                    for line in paragraph.lines:
                        lines += 1
                        runs += len(line.runs)

    profile = (doc.reconstruction_profile if doc else {}) or {}
    quality = (doc.quality if doc else {}) or {}

    legacy_pages = _read(art.project_dir / "pages", "page_*.html") if art.project_dir else []
    semantic_dir = art.project_dir / "pages_semantic" if art.project_dir else Path()
    semantic_pages = _read(semantic_dir, "page_*.html")
    css = (semantic_dir / "semantic.css")
    css_text = css.read_text(encoding="utf-8") if css.exists() else ""

    legacy_spans = sum(h.count("<span") for h in legacy_pages)
    semantic_spans = sum(h.count("<span") for h in semantic_pages)
    per_page_semantic_spans = [h.count("<span") for h in semantic_pages] or [0]

    fonts_total = len(doc.fonts) if doc else 0
    fonts_with_file = sum(1 for f in doc.fonts if f.filename) if doc else 0
    images_total = sum(len(p.images) for p in doc.pages) if doc else 0
    shapes_total = sum(len(p.shapes) for p in doc.pages) if doc else 0

    return {
        "name": art.name,
        "ok": art.ok,
        "error": art.error,
        "pages": len(doc.pages) if doc else 0,
        # Extraction Accuracy (M-R0): what extraction captured, as numbers,
        # so a defect is attributable to extraction vs rendering by data.
        # shapes_total is expected to be 0 until the shapes extractor lands
        # (roadmap M-R8) — reporting the 0 is the point: it makes the gap
        # visible per document instead of implicit.
        "extraction": {
            "chars_total": profile.get("chars_total", 0),
            "chars_substituted": profile.get("chars_substituted", 0),
            "fonts_total": fonts_total,
            "fonts_with_file": fonts_with_file,
            "images_total": images_total,
            "shapes_total": shapes_total,
        },
        "fidelity": {
            "chars_total": profile.get("chars_total", 0),
            "chars_substituted": profile.get("chars_substituted", 0),
            "chars_lost": profile.get("chars_lost", 0),
            "substitution_rate": profile.get("character_substitution_rate", 0.0),
        },
        "structure": {
            "regions": regions,
            "paragraphs": paragraphs,
            "lines": lines,
            "runs": runs,
            "low_confidence_paragraphs": low_conf_paras,
        },
        "rendering": {
            "legacy_spans": legacy_spans,
            "semantic_spans": semantic_spans,
            "span_reduction": legacy_spans - semantic_spans,
            "css_rules": css_text.count("{"),
            "semantic_html_bytes": sum(len(h.encode("utf-8")) for h in semantic_pages),
            "largest_page_spans": max(per_page_semantic_spans),
        },
        "performance": {
            "stage_seconds": dict(art.stage_timings),
            "total_seconds": round(sum(art.stage_timings.values()), 4),
        },
        "quality": {
            "overall_pass": quality.get("overall_pass"),
            "scorecard": quality.get("scorecard", {}),
            "stages": quality.get("stages", []),
        },
        # M-R1: the full fidelity hierarchy (Document Fidelity Measurement
        # Framework), recomputed here WITH the performance family populated
        # (only RVF knows the timings). Distinct key from the legacy
        # "fidelity" conservation counts above.
        "document_fidelity": _fidelity_with_performance(art),
    }


def _fidelity_with_performance(art: RunArtifacts) -> dict:
    if art.document is None:
        return {}
    pages = len(art.document.pages) or 1
    total_seconds = sum(art.stage_timings.values())
    return compute_document_fidelity(
        art.document,
        performance={"seconds_per_page": round(total_seconds / pages, 3)},
    )
