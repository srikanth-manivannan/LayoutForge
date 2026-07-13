"""Issue classification (RVF, Phase 2.7b; governed by docs/DEVELOPMENT_MODEL.md).

Turns raw validator violations and scorecard failures into a structured,
categorized backlog. Each issue carries its category, the EARLIEST responsible
stage, a P0–P4 severity (P0/P1 are release-blocking), a deterministic id, and
lifecycle metadata — so the corpus run answers "where was the first wrong
decision made, and does it block release?" automatically.
"""

import hashlib

from tools.rvf.pipeline import RunArtifacts

# code → (category, earliest responsible stage, severity)
_CODE_META: dict[str, tuple[str, str, str]] = {
    "character_loss": ("Unicode", "extraction", "P0"),
    "duplicate_node_id": ("Model", "reconstruct_tree", "P1"),
    "invalid_font_reference": ("Fonts", "font_resolution", "P1"),
    "word_fragment_mismatch": ("Typography", "word_builder", "P1"),
    "fragment_text_not_in_run": ("Typography", "word_builder", "P1"),
    "fragment_foreign_run": ("Typography", "word_builder", "P1"),
    "word_without_run": ("Typography", "word_builder", "P2"),
    "run_without_word": ("Typography", "word_builder", "P2"),
    "empty_run": ("Typography", "run_builder", "P2"),
    "line_without_runs": ("Layout", "line_builder", "P2"),
    "paragraph_without_lines": ("Layout", "paragraph_builder", "P2"),
    "baseline_inversion": ("Layout", "reading_order", "P3"),
}

# scorecard metric → (category, stage, severity)
_SCORECARD_META: dict[str, tuple[str, str, str]] = {
    "character_fidelity_pct": ("Unicode", "extraction", "P0"),
    "unicode_fidelity_pct": ("Unicode", "fonts", "P0"),
    "lexical_conservation_pct": ("Typography", "word_builder", "P1"),
    "font_resolution_pct": ("Fonts", "font_resolution", "P1"),
    # Rendering fidelity — the render leans on corrective styling. Earliest
    # responsible stage is font metrics (advance/tracking measurement).
    "glyph_escalation_rate": ("Rendering", "font_metrics", "P2"),
    "mean_reconstruction_confidence": ("Rendering", "font_metrics", "P2"),
    "mean_width_error_px": ("Rendering", "font_metrics", "P2"),
    "validator_errors": ("Model", "validator", "P1"),
}

SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
RELEASE_BLOCKING = {"P0", "P1"}


def _issue_id(code: str, page, message: str) -> str:
    digest = hashlib.sha1(f"{code}|{page}|{message}".encode("utf-8")).hexdigest()[:8]
    return f"{code}-{digest}"


def _issue(code: str, category: str, stage: str, severity: str, page, message: str) -> dict:
    return {
        "id": _issue_id(code, page, message),
        "category": category,
        "code": code,
        "stage": stage,
        "severity": severity,
        "release_blocking": severity in RELEASE_BLOCKING,
        "page": page,
        "message": message,
        # Lifecycle (populated as the issue is worked; deterministic id lets it
        # be tracked across runs — see docs/DEVELOPMENT_MODEL.md).
        "status": "Open",
        "detected_by": "RVF",
        "regression_test": None,
        "fixed_in": None,
        "verified_by": None,
    }


def classify(art: RunArtifacts) -> list[dict]:
    if not art.ok:
        return [_issue("pipeline_failure", "Pipeline", "unknown", "P0", None, art.error or "conversion failed")]

    document = art.document
    issues: list[dict] = []

    validation = (document.idm_validation if document else {}) or {}
    for violation in validation.get("violations", []):
        category, stage, severity = _CODE_META.get(violation["code"], ("Uncategorized", "unknown", "P2"))
        # A warning is never release-blocking, even for a normally-P0/P1 code.
        if violation.get("severity") == "warning" and severity in RELEASE_BLOCKING:
            severity = "P2"
        issues.append(_issue(violation["code"], category, stage, severity, violation.get("page"), violation.get("message", "")))

    scorecard = ((document.quality if document else {}) or {}).get("scorecard", {})
    for metric, entry in scorecard.items():
        if not entry.get("pass", True):
            category, stage, severity = _SCORECARD_META.get(metric, ("Quality", "unknown", "P1"))
            issues.append(_issue(f"scorecard:{metric}", category, stage, severity, None,
                                 f"{metric} {entry['current']} misses target {entry['target']}"))

    issues.sort(key=lambda i: SEVERITY_RANK.get(i["severity"], 9))
    return issues
