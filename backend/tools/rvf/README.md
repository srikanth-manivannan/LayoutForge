# Rendering Validation Framework (RVF)

Permanent compiler-validation infrastructure for LayoutForge. The engine is a
compiler (PDF → Rich IDM → output formats); RVF is its test harness + golden
corpus. It drives real PDFs through the **real** production pipeline, collects
per-document metrics, checks fidelity, diffs the legacy vs semantic writers,
and detects regressions against a baseline — with a versioned HTML dashboard.

## Run

```bash
# from backend/
python -m tools.rvf /path/to/corpus --out rvf_report --baseline rvf_baseline.json
```

- Searches `<corpus>` recursively for `*.pdf`.
- Writes `rvf_report/index.html` (dashboard), `summary.json`, `metrics.csv`.
- `--baseline FILE`: compare against it (created on first run); `--update-baseline`
  to overwrite. Exit code is non-zero on any failure or regression → CI-ready.
- `--dpi N`: background raster DPI (default 150; throughput vs fidelity).

## What it measures

- **Fidelity** — chars total / lost / substituted (chars_lost MUST be 0).
- **Authoritative parity** — semantic HTML text ↔ IDM tree text (extraction is
  the source of truth; the legacy writer is *not* the oracle — it carries its
  own artifacts like `﻿` joiners).
- **Structure** — regions / paragraphs / lines / runs, low-confidence paragraphs.
- **Rendering** — legacy vs semantic span counts (the span-explosion story),
  CSS-rule count, HTML size, largest page.
- **Performance** — per-stage and total time.
- **Provenance** — git commit, versions, feature flags, OS, Python — on every report.

## Modules

`runner` (orchestrate) · `pipeline` (drive one PDF) · `metrics` · `comparer`
(fidelity diff) · `baseline` (regression) · `report` (dashboard) · `env`
(provenance). Nothing here depends on a specific writer.
