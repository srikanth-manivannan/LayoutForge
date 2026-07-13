"""Corpus orchestrator (RVF). Discover PDFs, drive each through the real
pipeline, collect metrics + writer diffs, aggregate, detect regressions vs a
baseline, and emit reports. Built to run forever, not once."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from collections import Counter

from tools.rvf import artifacts, comparer, issues, metrics, report
from tools.rvf.baseline import detect_regressions, load_baseline, save_baseline
from tools.rvf.certification import certify
from tools.rvf.clusters import build_clusters
from tools.rvf.drift import aggregate_drift, drift_report
from tools.rvf.trends import append_history, load_history, trend_row
from tools.rvf.typography_clusters import aggregate_typography, analyze_document_fonts
from tools.rvf.env import capture_environment
from tools.rvf.pipeline import run_pdf


@dataclass
class CorpusResult:
    aggregates: dict
    records: list[dict]
    regressions: list[str]
    out_dir: Path


def _aggregate(records: list[dict], compares: dict[str, dict]) -> dict:
    total = len(records)
    ok = sum(1 for r in records if r["ok"])
    chars_total = sum(r["fidelity"]["chars_total"] for r in records)
    chars_lost = sum(r["fidelity"]["chars_lost"] for r in records)
    chars_sub = sum(r["fidelity"]["chars_substituted"] for r in records)
    unicode_fidelity = 100.0 * (1 - (chars_lost + chars_sub) / chars_total) if chars_total else 100.0
    parity_failures = sum(1 for c in compares.values() if c.get("comparable") and not c.get("unicode_parity"))
    quality_passes = sum(1 for r in records if r["quality"].get("overall_pass"))
    return {
        "quality_passes": quality_passes,
        "total": total,
        "ok": ok,
        "failed": total - ok,
        "chars_total": chars_total,
        "chars_lost": chars_lost,
        "chars_substituted": chars_sub,
        "unicode_fidelity_pct": round(unicode_fidelity, 6),
        "unicode_parity_failures": parity_failures,
        "legacy_spans": sum(r["rendering"]["legacy_spans"] for r in records),
        "semantic_spans": sum(r["rendering"]["semantic_spans"] for r in records),
        "span_reduction": sum(r["rendering"]["span_reduction"] for r in records),
        "largest_page_spans": max((r["rendering"]["largest_page_spans"] for r in records), default=0),
        "low_confidence_paragraphs": sum(r["structure"]["low_confidence_paragraphs"] for r in records),
        "total_seconds": round(sum(r["performance"]["total_seconds"] for r in records), 3),
    }


def discover(corpus_dir: Path) -> list[Path]:
    return sorted(p for p in corpus_dir.rglob("*.pdf") if p.is_file())


def _aggregate_fidelity(records: list[dict]) -> dict:
    """Corpus-level fidelity rollup (M-R1): per-family mean score (trend
    only) + gate pass counts, and gated overall passes. Never averages
    across families — overall stays AND-gated per document."""
    families: dict[str, dict] = {}
    overall_passes = 0
    for record in records:
        fidelity = record.get("document_fidelity") or {}
        if (fidelity.get("overall") or {}).get("pass"):
            overall_passes += 1
        for name, fam in (fidelity.get("families") or {}).items():
            slot = families.setdefault(name, {"scores": [], "gate_passes": 0, "with_data": 0})
            if fam.get("score") is not None:
                slot["scores"].append(fam["score"])
            if fam.get("gate_pass") is not None:
                slot["with_data"] += 1
                if fam["gate_pass"]:
                    slot["gate_passes"] += 1
    return {
        "overall_passes": overall_passes,
        "families": {
            name: {
                "mean_score": round(sum(s["scores"]) / len(s["scores"]), 4) if s["scores"] else None,
                "gate_passes": s["gate_passes"],
                "documents_with_data": s["with_data"],
            }
            for name, s in families.items()
        },
    }


def category_of(pdf: Path, corpus_dir: Path) -> str:
    """A document's category is its first directory under the corpus root
    (the golden-corpus layout); root-level files are 'uncategorized'."""
    rel = pdf.relative_to(corpus_dir)
    return rel.parts[0] if len(rel.parts) > 1 else "uncategorized"


def _aggregate_categories(records: list[dict], category_by_doc: dict[str, str]) -> dict:
    """Per-category benchmark rows for the dashboard (M-R0): pass rates,
    escalation/confidence means, issues — the 'know where to invest' table."""
    by_cat: dict[str, list[dict]] = {}
    for rec in records:
        by_cat.setdefault(category_by_doc.get(rec["name"], "uncategorized"), []).append(rec)

    out: dict[str, dict] = {}
    for cat, recs in sorted(by_cat.items()):
        scorecards = [r["quality"].get("scorecard", {}) for r in recs]
        escalations = [s.get("glyph_escalation_rate", {}).get("current") for s in scorecards]
        escalations = [e for e in escalations if isinstance(e, (int, float))]
        confidences = [s.get("mean_reconstruction_confidence", {}).get("current") for s in scorecards]
        confidences = [c for c in confidences if isinstance(c, (int, float))]
        out[cat] = {
            "documents": len(recs),
            "ok": sum(1 for r in recs if r["ok"]),
            "quality_passes": sum(1 for r in recs if r["quality"].get("overall_pass")),
            "chars_total": sum(r["fidelity"]["chars_total"] for r in recs),
            "chars_lost": sum(r["fidelity"]["chars_lost"] for r in recs),
            "mean_glyph_escalation": round(sum(escalations) / len(escalations), 4) if escalations else None,
            "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
            "total_seconds": round(sum(r["performance"]["total_seconds"] for r in recs), 2),
        }
    return out


def run_corpus(
    corpus_dir: Path,
    out_dir: Path,
    *,
    baseline_path: Path | None = None,
    update_baseline: bool = False,
    workspace_root: Path | None = None,
    dpi: int = 150,
) -> CorpusResult:
    env = capture_environment()
    pdfs = discover(corpus_dir)

    cleanup = None
    if workspace_root is None:
        cleanup = tempfile.TemporaryDirectory(prefix="rvf_ws_")
        workspace_root = Path(cleanup.name)

    documents_dir = out_dir / "documents"
    records: list[dict] = []
    compares: dict[str, dict] = {}
    issue_categories: Counter = Counter()
    issue_severities: Counter = Counter()
    issues_by_doc: dict[str, list[dict]] = {}
    category_by_doc: dict[str, str] = {}
    docs_per_category: Counter = Counter()
    drift_reports: list[dict] = []
    typography_rows: list[list[dict]] = []
    total_issues = 0
    try:
        for index, pdf in enumerate(pdfs, start=1):
            art = run_pdf(pdf, workspace_root / f"doc_{index:04d}", dpi=dpi)
            # Identity = corpus-relative path, not filename: two `doc.pdf`s in
            # different category folders must never collide in artifacts,
            # compares, or clusters (M-R0 collision fix).
            rel_name = pdf.relative_to(corpus_dir).as_posix()
            art.name = rel_name
            category = category_of(pdf, corpus_dir)
            category_by_doc[rel_name] = category
            docs_per_category[category] += 1

            record = metrics.collect(art)
            records.append(record)
            compares[rel_name] = comparer.compare(art)

            doc_issues = issues.classify(art)
            issues_by_doc[rel_name] = doc_issues
            total_issues += len(doc_issues)
            issue_categories.update(i["category"] for i in doc_issues)
            issue_severities.update(i["severity"] for i in doc_issues)
            if art.document is not None:
                drift_reports.append(drift_report(art.document))
                typography_rows.append(analyze_document_fonts(art.document, art.project_dir))
            artifacts.write_document_artifacts(art, record, doc_issues, documents_dir)

            status = "ok" if art.ok else f"FAIL ({art.error})"
            print(f"[{index}/{len(pdfs)}] {rel_name}: {status} · {len(doc_issues)} issues")
    finally:
        pass

    aggregates = _aggregate(records, compares)
    aggregates["total_issues"] = total_issues
    aggregates["issues_by_category"] = dict(issue_categories)
    aggregates["issues_by_severity"] = dict(issue_severities)
    aggregates["by_category"] = _aggregate_categories(records, category_by_doc)
    aggregates["clusters"] = build_clusters(issues_by_doc, category_by_doc, dict(docs_per_category))
    aggregates["fidelity"] = _aggregate_fidelity(records)
    aggregates["drift"] = aggregate_drift(drift_reports)
    aggregates["typography"] = aggregate_typography(typography_rows)
    aggregates["certification"] = certify(aggregates)
    baseline = load_baseline(baseline_path) if baseline_path else None
    regressions = detect_regressions(aggregates, baseline)

    # Trend history (M-R1): one row per run, persisted next to the baseline so
    # the dashboard shows direction (73% → 24% → …), not just a snapshot.
    history_rows: list[dict] = []
    if baseline_path is not None:
        history_path = baseline_path.with_suffix(".history.jsonl")
        append_history(history_path, trend_row(env, aggregates))
        history_rows = load_history(history_path)

    report.write_reports(out_dir, env, records, compares, aggregates, regressions, history=history_rows)
    if baseline_path and (update_baseline or baseline is None):
        save_baseline(aggregates, baseline_path)

    if cleanup is not None:
        cleanup.cleanup()
    return CorpusResult(aggregates=aggregates, records=records, regressions=regressions, out_dir=out_dir)
