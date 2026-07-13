"""Conversion report (M1.7 engine stabilization). A machine-readable
`report.json` per project: the reconstruction profile/analytics, per-stage
timing + peak memory, and a compact accuracy summary. This is the telemetry
that lets releases be compared objectively (v0.8 kerning 18% → v0.9 11% →
v1.0 4%) and that the Quality Gate checks against."""

import json
import logging
from pathlib import Path

from app.pipeline.document import Document
from app.pipeline.engine import StageMetric

logger = logging.getLogger("layoutforge.performance")

REPORT_VERSION = 1


def build_report(document: Document, stage_metrics: list[StageMetric]) -> dict:
    profile = document.reconstruction_profile or {}

    fonts_total = len(document.fonts)
    fonts_no_web_file = sum(1 for f in document.fonts if not f.filename)

    return {
        "report_version": REPORT_VERSION,
        "project_id": document.project_id,
        "pages": len(document.pages),
        "fonts": {
            "total": fonts_total,
            # A non-embeddable font is an expected fallback (base-14 maps to a
            # metric-compatible local); the Quality Gate cares about
            # UNEXPECTED fallbacks, which validation flags separately.
            "without_web_file": fonts_no_web_file,
        },
        "reconstruction_profile": profile,
        # Measured quality (Phase 2.7): per-stage conservation ledger +
        # release scorecard — the objective, comparable definition of "done".
        "quality": document.quality or {},
        # Character fidelity is the PRIMARY success criterion (Quality Gate):
        # a substituted char renders visibly in a fallback font; a LOST char
        # is structurally impossible (blank-mapping purge). chars_lost must
        # always be 0 — anything else fails the gate.
        "fidelity": {
            "chars_total": profile.get("chars_total", 0),
            "chars_lost": profile.get("chars_lost", 0),
            "chars_substituted": profile.get("chars_substituted", 0),
            "character_substitution_rate": profile.get("character_substitution_rate", 0.0),
        },
        "accuracy": {
            "glyph_fraction": profile.get("glyph_fraction", 0.0),
            "mean_reconstruction_confidence": profile.get("mean_reconstruction_confidence", 1.0),
        },
        "performance": {
            "stages": [
                {"stage": m.stage, "duration_seconds": m.duration_seconds, "peak_memory_mb": m.peak_memory_mb}
                for m in stage_metrics
            ],
            "total_duration_seconds": round(sum(m.duration_seconds for m in stage_metrics), 3),
            "peak_memory_mb": round(max((m.peak_memory_mb for m in stage_metrics), default=0.0), 2),
        },
    }


def write_report(report: dict, project_dir: Path) -> Path:
    path = project_dir / "report.json"
    try:
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001 - a report failure must never fail the conversion
        logger.warning("could not write conversion report to %s", path, exc_info=True)
    return path
