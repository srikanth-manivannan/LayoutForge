"""Rendering Validation Framework (RVF).

Permanent compiler-validation infrastructure for LayoutForge (ADR-011). The
engine is a compiler from PDF → Rich IDM → output formats; RVF is its test
harness + golden corpus, validating the compiler against a real document
corpus and diffing writers (legacy fixed-layout vs semantic) with regression
baselines and versioned reports.

Architecture (nothing here depends on a specific renderer):

    runner      → discover corpus, drive the pipeline per document
    pipeline    → run one PDF through the real stages into a temp workspace
    metrics     → fidelity / structure / rendering / performance per document
    comparer    → legacy ↔ semantic diffs (unicode / spans / css / size)
    baseline    → snapshot + regression detection across runs
    report      → summary.json + metrics.csv + index.html dashboard
    env         → version/commit/flags/OS/python provenance on every report
"""

RVF_VERSION = "0.1"
