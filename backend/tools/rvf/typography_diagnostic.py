"""Typography Measurement Diagnostic (Rendering Accuracy v1, step 1).

Diagnostics ONLY — this changes no engine code. For a converted project it
compares, per glyph, the PDF's ACTUAL advance (from PyMuPDF `get_texttrace()`
origins — ground truth, already including Tc/Tw/Tz/kerning) against LayoutForge's
NOMINAL font advance, and classifies WHY they differ:

    tracking  — constant additive excess per glyph  → un-extracted Tc/Tw
    scaling   — constant ratio ≠ 1                   → un-extracted Tz
    kerning   — variable, centred near 0             → GPOS/TJ kerning
    metrics   — large, and a single-cause model explains most of it
    unknown   — large, and NO single-cause model fits well → next work item
    ok        — within tolerance

Every span gets an explicit cause, including `unknown` — forcing every span
into a wrong bucket (e.g. always "metrics") would hide the diagnostic's own
blind spots. A high `unknown` fraction means the classifier itself needs a
new cause, not that the document is fine.

Answers "what did the PDF render vs what did we measure, and why?" with
evidence, so the engine fix targets the earliest real cause instead of guessing.
Emits `typography.json` next to `report.json`.
"""

import json
from pathlib import Path
from statistics import mean, median, pstdev

import fitz

from app.pipeline.document import Document
from app.pipeline.typography.font_metrics import load_font_metrics

_TOL_PX = 0.3          # per-glyph diff below this is negligible
_SCALE_TOL = 0.02      # |ratio − 1| below this is not scaling


def classify_advances(pairs: list[tuple[float, float]]) -> dict:
    """`pairs` = [(actual_px, nominal_px), …] for non-space, measurable glyphs."""
    pairs = [(a, n) for a, n in pairs if n > 0]
    if len(pairs) < 2:
        return {"cause": "unmeasurable", "glyphs": len(pairs)}
    diffs = [a - n for a, n in pairs]
    ratios = [a / n for a, n in pairs]
    med_diff = median(diffs)
    mean_ratio = mean(ratios)
    mean_abs = mean(abs(d) for d in diffs)
    add_residual = pstdev([d - med_diff for d in diffs])          # fit: actual = nominal + Tc
    mult_residual = pstdev([a - n * mean_ratio for a, n in pairs])  # fit: actual = nominal × Th

    # A "good fit" means the residual is small relative to the effect it's
    # explaining (or in absolute terms, for small effects) — not merely
    # smaller than the alternative model's residual.
    def good_fit(residual: float, magnitude: float) -> bool:
        return residual <= max(0.15, 0.3 * abs(magnitude))

    if mean_abs <= _TOL_PX:
        cause = "ok"
    elif abs(med_diff) > _TOL_PX and add_residual <= mult_residual and good_fit(add_residual, med_diff):
        cause = "tracking"
    elif abs(mean_ratio - 1.0) > _SCALE_TOL and mult_residual < add_residual and good_fit(mult_residual, mean_abs):
        cause = "scaling"
    elif abs(med_diff) <= _TOL_PX:
        cause = "kerning"
    elif good_fit(add_residual, mean_abs) or good_fit(mult_residual, mean_abs):
        cause = "metrics"
    else:
        cause = "unknown"
    return {
        "cause": cause,
        "glyphs": len(pairs),
        "tracking_px": round(med_diff, 3),
        "scale": round(mean_ratio, 4),
        "mean_diff_px": round(mean(diffs), 3),
        "add_residual_px": round(add_residual, 3),
        "mult_residual_px": round(mult_residual, 3),
    }


def _load_metrics_by_name(document: Document, fonts_dir: Path) -> dict:
    metrics: dict[str, object] = {}
    for font in document.fonts:
        if not font.filename:
            continue
        loaded = load_font_metrics(fonts_dir / font.filename)
        if loaded is None:
            continue
        for key in {font.family, font.original_name}:
            metrics.setdefault(key, loaded)
    return metrics


def diagnose(document: Document, project_dir: Path, max_pages: int | None = None,
             max_span_samples: int = 40) -> dict:
    """Core diagnostic over an in-memory Document + its project dir (source.pdf
    + resources/fonts). Returns the report; does not write it."""
    project_dir = Path(project_dir)
    metrics_by_name = _load_metrics_by_name(document, project_dir / "resources" / "fonts")

    cause_counts: dict[str, int] = {}
    tracking_values: list[float] = []
    samples: list[dict] = []

    with fitz.open(project_dir / "source.pdf") as pdf:
        for index, page in enumerate(pdf, start=1):
            if max_pages and index > max_pages:
                break
            for span in page.get_texttrace():
                metrics = metrics_by_name.get(span.get("font", ""))
                chars = span.get("chars", [])
                if metrics is None or len(chars) < 3:
                    continue
                size = span.get("size", 0.0)
                xs = [c[2][0] for c in chars]
                codes = [c[0] for c in chars]
                pairs: list[tuple[float, float]] = []
                for i in range(len(chars) - 1):
                    ch = chr(codes[i])
                    if ch.isspace():
                        continue
                    adv = metrics.advance(ch)
                    if adv is None:
                        continue
                    pairs.append((xs[i + 1] - xs[i], adv / metrics.units_per_em * size))
                result = classify_advances(pairs)
                cause = result["cause"]
                cause_counts[cause] = cause_counts.get(cause, 0) + 1
                if cause == "tracking":
                    tracking_values.append(result["tracking_px"])
                if len(samples) < max_span_samples:
                    text = "".join(chr(c[0]) for c in chars if c[0])
                    samples.append({"page": index, "font": span.get("font"), "size": round(size, 2),
                                    "text": text[:40], **result})

    total = sum(cause_counts.values()) or 1
    summary = {
        "spans_analyzed": sum(cause_counts.values()),
        "cause_counts": cause_counts,
        "cause_fractions": {c: round(n / total, 4) for c, n in cause_counts.items()},
        "dominant_cause": max(cause_counts, key=cause_counts.get) if cause_counts else None,
        "median_tracking_px": round(median(tracking_values), 3) if tracking_values else 0.0,
    }
    return {"project_id": document.project_id, "summary": summary, "samples": samples}


def diagnose_project(project_dir: Path, max_pages: int | None = None, max_span_samples: int = 40) -> dict:
    """Convenience wrapper: load idm.json, diagnose, and write typography.json."""
    project_dir = Path(project_dir)
    document = Document.from_dict(json.loads((project_dir / "idm.json").read_text(encoding="utf-8")))
    report = diagnose(document, project_dir, max_pages=max_pages, max_span_samples=max_span_samples)
    (project_dir / "typography.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
