"""Core v1 Certification (RVF; docs/DEVELOPMENT_MODEL.md).

Evaluates a corpus run against the release bar that must hold before Phase 3
(Document Intelligence): zero release-blocking issues (P0/P1), zero pipeline
failures, the quality scorecard passing on every document, and legacy↔semantic
parity. Certification is the permanent baseline — it turns "looks good" into an
objective, re-checkable verdict.
"""


def certify(aggregates: dict) -> dict:
    severities = aggregates.get("issues_by_severity", {})
    p0 = severities.get("P0", 0)
    p1 = severities.get("P1", 0)
    total = aggregates.get("total", 0)

    criteria = {
        "no_p0_issues": {"pass": p0 == 0, "detail": f"{p0} P0 (release-blocking)"},
        "no_p1_issues": {"pass": p1 == 0, "detail": f"{p1} P1 (release-blocking)"},
        "no_pipeline_failures": {"pass": aggregates.get("failed", 0) == 0, "detail": f"{aggregates.get('failed', 0)} failed"},
        "quality_all_pass": {
            "pass": total > 0 and aggregates.get("quality_passes", 0) == total,
            "detail": f"{aggregates.get('quality_passes', 0)}/{total} scorecards pass",
        },
        "semantic_parity": {
            "pass": aggregates.get("unicode_parity_failures", 0) == 0,
            "detail": f"{aggregates.get('unicode_parity_failures', 0)} parity failures",
        },
    }
    certified = total > 0 and all(c["pass"] for c in criteria.values())
    return {"certified": certified, "criteria": criteria}
