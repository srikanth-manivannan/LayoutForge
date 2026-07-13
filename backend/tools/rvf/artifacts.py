"""Per-document artifacts (RVF, Phase 2.7b).

Every corpus document produces a self-contained evidence bundle, so any single
conversion is fully inspectable long after the run:

    documents/<name>/
      report.json          compact per-doc summary
      validator.json       Rich IDM validation (violations)
      quality.json         per-stage ledger + scorecard
      performance.json     per-stage timings
      reconstruction.json  structure counts + reconstruction profile
      issues.json          classified backlog for this document

(Visual artifacts — comparison.png / diff heatmaps — land with the Playwright
decision; they are intentionally not emitted here.)
"""

import json
import re
from pathlib import Path

from tools.rvf.drift import drift_report
from tools.rvf.pipeline import RunArtifacts
from tools.rvf.typography_diagnostic import diagnose


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "doc"


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_document_artifacts(art: RunArtifacts, record: dict, issues: list[dict], documents_dir: Path) -> Path:
    doc_dir = documents_dir / _safe(art.name)
    doc_dir.mkdir(parents=True, exist_ok=True)
    document = art.document

    _write(doc_dir / "report.json", {
        "name": art.name, "ok": art.ok, "error": art.error, "pages": record["pages"],
        "fidelity": record["fidelity"], "quality_overall_pass": record["quality"].get("overall_pass"),
    })
    _write(doc_dir / "validator.json", (document.idm_validation if document else {}) or {})
    _write(doc_dir / "quality.json", (document.quality if document else {}) or {})
    _write(doc_dir / "performance.json", record["performance"])
    _write(doc_dir / "reconstruction.json", {
        "structure": record["structure"],
        "reconstruction_profile": (document.reconstruction_profile if document else {}) or {},
    })
    _write(doc_dir / "issues.json", {"count": len(issues), "issues": issues})

    # Typography diagnostic (best-effort — never fail the corpus run over it).
    if document is not None and art.project_dir is not None:
        try:
            _write(doc_dir / "typography.json", diagnose(document, art.project_dir))
        except Exception:  # noqa: BLE001 - diagnostic is advisory
            pass

    # Drift diagnostics (M-R2a): per-page / per-font / per-reason statistics
    # + worst offenders — the before/after evidence for Typography
    # Measurement Engine v2.
    if document is not None:
        try:
            _write(doc_dir / "drift.json", drift_report(document))
        except Exception:  # noqa: BLE001 - diagnostic is advisory
            pass
    return doc_dir
