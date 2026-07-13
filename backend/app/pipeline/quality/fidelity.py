"""Document Fidelity Measurement Framework (M-R1).

The stable, extensible score hierarchy every later milestone reports into:

    Overall Fidelity
      ├── Extraction   (unicode, characters, lexical, fonts)
      ├── Typography   (baseline, line-height, word drift, tracking, kerning*)
      ├── Layout       (paragraph rhythm, margins*, alignment*, columns*)
      ├── Semantic     (reading order*, paragraphs*, lists*, tables*, headings*)
      ├── Rendering    (escalation, confidence, browser*, pixel*)
      └── Performance  (time, memory — populated by RVF, not the pipeline)
                                                     * = reserved slot

Reserved slots exist NOW (current=None, source="reserved") so score semantics
never change when Phase 3 / the browser oracle populate them.

Every metric carries {current, target, pass, confidence, source}:
- `confidence` — how much to trust the MEASUREMENT itself (a conservation
  count is 1.0; a modeled static-geometry estimate is <1.0);
- `source` — where the number came from (conservation_ledger,
  static_geometry, static_geometry_model, reconstruction_profile, rvf,
  browser_oracle later, reserved). Static and browser measurements of the
  same quantity can coexist and be compared.

**Gating, not averaging.** Overall pass = AND over the critical families'
gates (a family gate = all its populated metrics pass). A numeric score per
family exists ONLY for trend reporting and is the MINIMUM of its members'
normalized scores (weakest link) — never the mean, so Typography=100% can
never mask Rendering=20%.

Measurement-only: this module reads the Document; it never mutates it and
never changes engine behavior.
"""

from dataclasses import dataclass
from statistics import median, pstdev

from app.pipeline.document import Document

# Families whose gate failure fails Overall. Reserved-only families
# (semantic today) and optional families (performance in-pipeline) do not
# gate until they have populated metrics.
CRITICAL_FAMILIES = ("extraction", "typography", "layout", "rendering")


@dataclass
class Metric:
    name: str
    current: float | None  # None = no data / reserved → excluded from gate
    target: float
    lower_is_better: bool = False
    confidence: float = 1.0
    source: str = "static_geometry"
    unit: str = ""

    @property
    def passed(self) -> bool | None:
        if self.current is None:
            return None
        return self.current <= self.target if self.lower_is_better else self.current >= self.target

    @property
    def score(self) -> float | None:
        """Normalized [0,1] — FOR TRENDS ONLY; gates decide pass/fail."""
        if self.current is None:
            return None
        if self.lower_is_better:
            if self.current <= self.target:
                return 1.0
            return max(0.0, min(1.0, self.target / self.current)) if self.current > 0 else 0.0
        return max(0.0, min(1.0, self.current / self.target)) if self.target > 0 else 1.0

    def to_dict(self) -> dict:
        return {
            "metric": self.name,
            "current": self.current,
            "target": self.target,
            "pass": self.passed,
            "confidence": self.confidence,
            "source": self.source,
            "unit": self.unit,
        }


def _reserved(name: str, target: float, lower: bool = False, unit: str = "") -> Metric:
    return Metric(name, None, target, lower_is_better=lower, confidence=0.0, source="reserved", unit=unit)


def _family(name: str, metrics: list[Metric], gates_overall: bool) -> dict:
    populated = [m for m in metrics if m.current is not None]
    gate = all(m.passed for m in populated) if populated else None  # None = no data yet
    scores = [m.score for m in populated if m.score is not None]
    return {
        "family": name,
        "gate_pass": gate,
        "gates_overall": gates_overall,
        # Weakest link, deliberately NOT a mean (see module docstring).
        "score": round(min(scores), 4) if scores else None,
        "metrics": [m.to_dict() for m in metrics],
    }


# ---------------------------------------------------------------------------
# Static measurements (from the Document + reconstruction decisions only)
# ---------------------------------------------------------------------------

def _iter_words(document: Document):
    for page in document.pages:
        for block in page.text_blocks:
            yield from block.words


def _iter_paragraphs(document: Document):
    for page in document.pages:
        for region in page.regions:
            yield from region.paragraphs


def _baseline_error_px(document: Document) -> float | None:
    """Modeled first-line baseline error of the legacy positioned output.
    CSS inline layout centers the glyph box in the line box (half-leading):
    rendered_baseline ≈ block_top + (L − (asc−desc)·size)/2 + asc·size.
    A MODEL of browser behavior (browsers use the font's own hhea/OS2
    ascent, which can differ from PyMuPDF's ascender) — hence source
    static_geometry_model, confidence < 1. The browser oracle (M-R5)
    re-measures this exactly."""
    errors: list[float] = []
    for page in document.pages:
        for block in page.text_blocks:
            if block.rotation != 0.0 or block.font_size <= 0:
                continue
            line_height = block.line_height or block.font_size * 1.2
            glyph_box = (block.ascender - block.descender) * block.font_size
            rendered = block.bbox.y + (line_height - glyph_box) / 2 + block.ascender * block.font_size
            errors.append(abs(rendered - block.origin_y))
    return round(median(errors), 3) if errors else None


def _line_height_deviation_px(document: Document) -> float | None:
    """Emitted line-height vs the PDF's actual baseline-to-baseline gaps
    inside multi-line paragraphs (the Rich IDM tree carries real baselines)."""
    deviations: list[float] = []
    for paragraph in _iter_paragraphs(document):
        lines = paragraph.lines
        if len(lines) < 2 or paragraph.line_height <= 0:
            continue
        for previous, current in zip(lines, lines[1:]):
            gap = current.baseline_y - previous.baseline_y
            if gap > 0:
                deviations.append(abs(gap - paragraph.line_height))
    return round(median(deviations), 3) if deviations else None


def _word_drift_px(document: Document) -> float | None:
    """Per-word endpoint drift proxy: word starts are pinned exactly (legacy)
    so a word's rendered extent deviates from the PDF's by |width_error|.
    A PROXY (advance-based measurement in M-R2 replaces it) — flagged via
    confidence/source, not hidden."""
    errors = [abs(w.width_error) for w in _iter_words(document) if w.text.strip()]
    return round(median(errors), 3) if errors else None


def _tracking_residual_px(document: Document) -> float | None:
    """Residual width error on words whose escalation reason is tracking —
    how well measured Tc explains display-text geometry."""
    residuals = [abs(w.width_error) for w in _iter_words(document) if w.reason == "tracking"]
    return round(median(residuals), 3) if residuals else None


def _paragraph_rhythm_px(document: Document) -> float | None:
    """Spread of baseline gaps within paragraphs (rhythm regularity)."""
    spreads: list[float] = []
    for paragraph in _iter_paragraphs(document):
        gaps = [
            b.baseline_y - a.baseline_y
            for a, b in zip(paragraph.lines, paragraph.lines[1:])
            if b.baseline_y > a.baseline_y
        ]
        if len(gaps) >= 2:
            spreads.append(pstdev(gaps))
    return round(median(spreads), 3) if spreads else None


# ---------------------------------------------------------------------------
# The framework
# ---------------------------------------------------------------------------

def compute_document_fidelity(document: Document, performance: dict | None = None) -> dict:
    """The full hierarchy for one document. `performance` (seconds/memory) is
    supplied by RVF when available; absent in-pipeline → family has no data."""
    profile = document.reconstruction_profile or {}
    chars_total = profile.get("chars_total", 0)
    chars_lost = profile.get("chars_lost", 0)
    substitution_rate = profile.get("character_substitution_rate", 0.0)

    run_font_ids = [
        run.font_id
        for page in document.pages
        for region in page.regions
        for paragraph in region.paragraphs
        for line in paragraph.lines
        for run in line.runs
        if run.font_id
    ]
    known_fonts = {font.id for font in document.fonts}
    font_resolution = (
        100.0 * sum(1 for fid in run_font_ids if fid in known_fonts) / len(run_font_ids)
        if run_font_ids else None
    )

    extraction = [
        Metric("character_fidelity_pct",
               round(100.0 * (1 - chars_lost / chars_total), 4) if chars_total else None,
               100.0, source="conservation_ledger", unit="%"),
        Metric("unicode_fidelity_pct", round(100.0 * (1 - substitution_rate), 4),
               100.0, source="conservation_ledger", unit="%"),
        Metric("font_resolution_pct",
               round(font_resolution, 4) if font_resolution is not None else None,
               99.9, source="conservation_ledger", unit="%"),
        _reserved("image_fidelity_pct", 99.0, unit="%"),   # M-R8
        _reserved("shape_fidelity_pct", 99.0, unit="%"),   # M-R8
        _reserved("metadata_fidelity_pct", 100.0, unit="%"),
    ]

    typography = [
        Metric("baseline_error_px", _baseline_error_px(document), 0.5,
               lower_is_better=True, confidence=0.85, source="static_geometry_model", unit="px"),
        Metric("line_height_deviation_px", _line_height_deviation_px(document), 0.5,
               lower_is_better=True, confidence=0.95, source="static_geometry", unit="px"),
        Metric("word_drift_px", _word_drift_px(document), 0.25,
               lower_is_better=True, confidence=0.8, source="static_geometry", unit="px"),
        Metric("tracking_residual_px", _tracking_residual_px(document), 0.5,
               lower_is_better=True, confidence=0.9, source="reconstruction_profile", unit="px"),
        _reserved("kerning_error_px", 0.25, lower=True, unit="px"),        # M-R3/M-R5
        _reserved("letter_spacing_error_px", 0.25, lower=True, unit="px"), # M-R5
    ]

    layout = [
        Metric("paragraph_rhythm_px", _paragraph_rhythm_px(document), 1.0,
               lower_is_better=True, confidence=0.9, source="static_geometry", unit="px"),
        _reserved("margin_error_px", 1.0, lower=True, unit="px"),   # Phase 3
        _reserved("alignment_error_px", 1.0, lower=True, unit="px"),
        _reserved("column_accuracy_pct", 99.0, unit="%"),
    ]

    semantic = [
        _reserved("reading_order_accuracy_pct", 99.0, unit="%"),  # Phase 3, first
        _reserved("paragraph_accuracy_pct", 99.0, unit="%"),
        _reserved("list_accuracy_pct", 99.0, unit="%"),
        _reserved("table_accuracy_pct", 99.0, unit="%"),
        _reserved("heading_accuracy_pct", 99.0, unit="%"),
    ]

    rendering = [
        Metric("glyph_escalation_rate", round(profile.get("glyph_fraction", 0.0), 4), 0.10,
               lower_is_better=True, source="reconstruction_profile"),
        Metric("mean_reconstruction_confidence",
               round(profile.get("mean_reconstruction_confidence", 1.0), 4), 0.99,
               source="reconstruction_profile"),
        _reserved("browser_geometry_error_px", 0.25, lower=True, unit="px"),  # M-R5 oracle
        _reserved("pixel_fidelity_pct", 99.0, unit="%"),                      # M-R5 pixel diff
    ]

    performance_metrics = [
        Metric("seconds_per_page", performance.get("seconds_per_page"), 5.0,
               lower_is_better=True, source="rvf", unit="s")
        if performance and performance.get("seconds_per_page") is not None
        else _reserved("seconds_per_page", 5.0, lower=True, unit="s"),
        _reserved("peak_memory_mb_per_100_pages", 500.0, lower=True, unit="MB"),
    ]

    families = {
        "extraction": _family("extraction", extraction, True),
        "typography": _family("typography", typography, True),
        "layout": _family("layout", layout, True),
        "semantic": _family("semantic", semantic, False),
        "rendering": _family("rendering", rendering, True),
        "performance": _family("performance", performance_metrics, False),
    }

    # GATED overall: AND over critical families that HAVE data. Explicitly
    # not an average; a single failing critical family fails the document.
    critical = [families[name]["gate_pass"] for name in CRITICAL_FAMILIES]
    populated = [gate for gate in critical if gate is not None]
    overall_pass = bool(populated) and all(populated)
    family_scores = [f["score"] for f in families.values() if f["score"] is not None]

    return {
        "families": families,
        "overall": {
            "pass": overall_pass,
            # Weakest-link score for trending only (min, never mean).
            "score": round(min(family_scores), 4) if family_scores else None,
            "gating": "AND over critical families (extraction, typography, layout, rendering)",
        },
    }
