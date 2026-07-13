"""Report generation (RVF): summary.json + metrics.csv + a self-contained
index.html dashboard. One click, readable by a human or a CI artifact viewer."""

import csv
import json
from html import escape
from pathlib import Path


def _tile(label: str, value: str, warn: bool = False) -> str:
    cls = "tile warn" if warn else "tile"
    return f'<div class="{cls}"><div class="v">{escape(value)}</div><div class="l">{escape(label)}</div></div>'


def _row(rec: dict, cmp: dict) -> str:
    f = rec["fidelity"]
    s = rec["structure"]
    r = rec["rendering"]
    status = "ok" if rec["ok"] else "fail"
    parity = "✓" if cmp.get("unicode_parity") else ("—" if not cmp.get("comparable") else "✗")
    cells = [
        escape(rec["name"]),
        f'<span class="{status}">{status}</span>',
        str(rec["pages"]),
        f'{f["chars_total"]:,}',
        str(f["chars_lost"]),
        str(f["chars_substituted"]),
        f'{s["paragraphs"]:,}',
        f'{s["runs"]:,}',
        f'{r["legacy_spans"]:,}',
        f'{r["semantic_spans"]:,}',
        f'{r["span_reduction"]:,}',
        str(r["css_rules"]),
        parity,
        f'{rec["performance"]["total_seconds"]:.2f}s',
    ]
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _category_section(agg: dict) -> str:
    """Benchmark Dashboard (M-R0): per-category rows — where to invest."""
    by_category = agg.get("by_category", {})
    if not by_category:
        return ""
    cat_head = "".join(f"<th>{h}</th>" for h in
                       ["Category", "Docs", "OK", "Quality pass", "Chars", "Lost", "Escalation", "Confidence", "Time"])
    cat_rows = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in [
            escape(cat), v["documents"], v["ok"], v["quality_passes"],
            f'{v["chars_total"]:,}', v["chars_lost"],
            "—" if v["mean_glyph_escalation"] is None else f'{v["mean_glyph_escalation"]:.2%}',
            "—" if v["mean_confidence"] is None else f'{v["mean_confidence"]:.3f}',
            f'{v["total_seconds"]:.1f}s',
        ]) + "</tr>"
        for cat, v in by_category.items()
    )
    return (f'<div class="wrap"><h2>By category</h2><div class="scroll"><table>'
            f"<thead><tr>{cat_head}</tr></thead><tbody>{cat_rows}</tbody></table></div></div>")


def _cluster_section(agg: dict) -> str:
    """Failure clusters (M-R0): fix clusters, not documents."""
    clusters = agg.get("clusters", [])
    if not clusters:
        return ""
    cl_head = "".join(f"<th>{h}</th>" for h in
                      ["Cluster", "Stage", "Sev", "Docs", "Categories", "Occurrences", "Max cat %", "Significant"])
    cl_rows = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in [
            escape(cl["code"]), escape(cl["stage"]), cl["severity"],
            cl["document_count"], escape(", ".join(cl["categories"])),
            cl["occurrences"], f'{cl["max_category_fraction"]:.0%}',
            "✔" if cl["significant"] else "—",
        ]) + "</tr>"
        for cl in clusters
    )
    return (f'<div class="wrap"><h2>Failure clusters</h2><div class="scroll"><table>'
            f"<thead><tr>{cl_head}</tr></thead><tbody>{cl_rows}</tbody></table></div></div>")


def _dashboard(env: dict, agg: dict, records: list[dict], compares: dict[str, dict], regressions: list[str]) -> str:
    cert = agg.get("certification", {})
    certified = cert.get("certified", False)
    tiles = "".join([
        _tile("Core v1", "CERTIFIED" if certified else "not certified", warn=not certified),
        _tile("Documents", f'{agg["total"]:,}'),
        _tile("Succeeded", f'{agg["ok"]:,}'),
        _tile("Failed", f'{agg["failed"]:,}', warn=agg["failed"] > 0),
        _tile("Unicode fidelity", f'{agg["unicode_fidelity_pct"]:.4f}%', warn=agg["unicode_fidelity_pct"] < 100),
        _tile("Chars lost", f'{agg["chars_lost"]:,}', warn=agg["chars_lost"] > 0),
        _tile("Legacy↔semantic parity", f'{agg["total"] - agg["unicode_parity_failures"]}/{agg["total"]}', warn=agg["unicode_parity_failures"] > 0),
        _tile("Quality pass", f'{agg["quality_passes"]}/{agg["total"]}', warn=agg["quality_passes"] < agg["total"]),
        _tile("Open issues", f'{agg.get("total_issues", 0):,}', warn=agg.get("total_issues", 0) > 0),
        _tile("Span reduction", f'{agg["span_reduction"]:,}'),
        _tile("Total time", f'{agg["total_seconds"]:.1f}s'),
    ])
    reg_html = ""
    if regressions:
        items = "".join(f"<li>{escape(x)}</li>" for x in regressions)
        reg_html = f'<div class="regressions"><h2>⚠ Regressions vs baseline</h2><ul>{items}</ul></div>'

    cat_html = _category_section(agg)
    cluster_html = _cluster_section(agg)
    headers = ["Document", "Status", "Pages", "Chars", "Lost", "Subst.", "Paras", "Runs",
               "Legacy spans", "Semantic spans", "Δ spans", "CSS", "Parity", "Time"]
    thead = "".join(f"<th>{h}</th>" for h in headers)
    rows = "".join(_row(rec, compares.get(rec["name"], {})) for rec in records)
    provenance = " · ".join(f"{k}: {escape(str(v))}" for k, v in env.items() if k != "feature_flags")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>RVF Report</title>
<style>
 body{{font:14px system-ui,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}}
 header{{padding:20px 28px;background:#151922;border-bottom:1px solid #262b36}}
 h1{{margin:0 0 6px;font-size:20px}} .prov{{color:#8b93a1;font-size:12px}}
 .tiles{{display:flex;flex-wrap:wrap;gap:12px;padding:20px 28px}}
 .tile{{background:#1a1f29;border:1px solid #262b36;border-radius:10px;padding:14px 18px;min-width:130px}}
 .tile.warn{{border-color:#7a4a12;background:#241a10}}
 .tile .v{{font-size:22px;font-weight:600}} .tile .l{{color:#8b93a1;font-size:12px;margin-top:4px}}
 table{{width:100%;border-collapse:collapse;font-size:13px}}
 th,td{{padding:8px 10px;text-align:right;border-bottom:1px solid #21262f}} th{{color:#8b93a1;text-align:right;position:sticky;top:0;background:#151922}}
 td:first-child,th:first-child{{text-align:left}}
 .ok{{color:#4ec06e}} .fail{{color:#e0564b}}
 .regressions{{margin:0 28px;padding:14px 18px;background:#241a10;border:1px solid #7a4a12;border-radius:10px}}
 .wrap{{padding:12px 28px 40px}} .scroll{{overflow-x:auto;border:1px solid #262b36;border-radius:10px}}
</style></head><body>
<header><h1>Rendering Validation Framework — Benchmark Report</h1><div class="prov">{provenance}</div></header>
<div class="tiles">{tiles}</div>
{reg_html}
{cat_html}
{cluster_html}
<div class="wrap"><h2>Documents</h2><div class="scroll"><table><thead><tr>{thead}</tr></thead><tbody>{rows}</tbody></table></div></div>
</body></html>
"""


_DASH_STYLE = """
 body{font:14px system-ui,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}
 header{padding:20px 28px;background:#151922;border-bottom:1px solid #262b36}
 h1{margin:0 0 6px;font-size:20px} h2{font-size:15px;color:#aab3c0} .prov{color:#8b93a1;font-size:12px}
 .tiles{display:flex;flex-wrap:wrap;gap:12px;padding:20px 28px}
 .tile{background:#1a1f29;border:1px solid #262b36;border-radius:10px;padding:14px 18px;min-width:150px}
 .tile.pass{border-color:#1d5230} .tile.fail{border-color:#7a2a24;background:#241512}
 .tile.nodata{opacity:.55}
 .tile .v{font-size:22px;font-weight:600} .tile .l{color:#8b93a1;font-size:12px;margin-top:4px}
 .tile .g{font-size:11px;margin-top:2px} .g.ok{color:#4ec06e} .g.bad{color:#e0564b} .g.na{color:#8b93a1}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th,td{padding:8px 10px;text-align:right;border-bottom:1px solid #21262f}
 th{color:#8b93a1;position:sticky;top:0;background:#151922}
 td:first-child,th:first-child{text-align:left}
 .wrap{padding:12px 28px 24px} .scroll{overflow-x:auto;border:1px solid #262b36;border-radius:10px}
 .up{color:#4ec06e}.down{color:#e0564b}
"""


def _gauge(label: str, score, gate, gates_overall: bool) -> str:
    if gate is None:
        cls, gate_text, gate_cls = "tile nodata", "no data", "na"
    elif gate:
        cls, gate_text, gate_cls = "tile pass", "gate PASS", "ok"
    else:
        cls, gate_text, gate_cls = "tile fail", "gate FAIL", "bad"
    value = "—" if score is None else f"{score:.0%}" if score <= 1 else str(score)
    suffix = " · gates overall" if gates_overall else ""
    return (f'<div class="{cls}"><div class="v">{value}</div>'
            f'<div class="l">{escape(label)}</div>'
            f'<div class="g {gate_cls}">{gate_text}{escape(suffix)}</div></div>')


def _trend_table(history: list[dict]) -> str:
    if len(history) < 1:
        return ""
    columns = [
        ("quality_passes", "Quality pass"), ("total_issues", "Issues"),
        ("chars_lost", "Chars lost"), ("span_reduction", "Span reduction"),
        ("total_seconds", "Time (s)"),
    ]
    head = "<th>Run</th><th>Commit</th><th>Docs</th>" + "".join(f"<th>{h}</th>" for _, h in columns)
    rows = ""
    for row in history:
        cells = f'<td>{escape(str(row.get("timestamp", ""))[:16])}</td><td>{escape(str(row.get("git_commit")))}</td><td>{row.get("documents")}</td>'
        for key, _ in columns:
            cells += f"<td>{row.get(key)}</td>"
        rows += f"<tr>{cells}</tr>"
    fam_names = sorted({k for row in history for k in (row.get("family_scores") or {})})
    fam_head = "<th>Run</th>" + "".join(f"<th>{escape(f)}</th>" for f in fam_names)
    fam_rows = ""
    for row in history:
        cells = f'<td>{escape(str(row.get("timestamp", ""))[:16])}</td>'
        for name in fam_names:
            value = (row.get("family_scores") or {}).get(name)
            cells += f'<td>{"—" if value is None else f"{value:.0%}"}</td>'
        fam_rows += f"<tr>{cells}</tr>"
    return (f'<div class="wrap"><h2>Trends (last {len(history)} runs)</h2>'
            f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<h2>Family scores over runs</h2>'
            f'<div class="scroll"><table><thead><tr>{fam_head}</tr></thead><tbody>{fam_rows}</tbody></table></div></div>')


def _drift_section(agg: dict) -> str:
    """M-R2a: per-font and per-reason drift — 'one font engine or the general
    algorithm?' answered at a glance."""
    drift = agg.get("drift", {})
    if not drift.get("by_font") and not drift.get("by_reason"):
        return ""

    def table(title: str, rows_by_key: dict, extra_col: str | None = None) -> str:
        head_cols = ["", "Words", "Mean px", "Median px", "p95 px", "Max px"]
        if extra_col:
            head_cols.append(extra_col)
        head = "".join(f"<th>{h}</th>" for h in head_cols)
        rows = ""
        for key, stats in rows_by_key.items():
            cells = [escape(key), stats["count"], stats["mean"], stats["median"], stats["p95"], stats["max"]]
            if extra_col:
                cells.append(f'{stats.get("contribution_pct", 0)}%')
            rows += "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
        return (f'<h2>{escape(title)}</h2><div class="scroll"><table>'
                f"<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>")

    return ('<div class="wrap">'
            + table("Drift by font", drift.get("by_font", {}))
            + table("Drift by reconstruction reason", drift.get("by_reason", {}), extra_col="Contribution")
            + "</div>")


def _typography_section(agg: dict) -> str:
    """M-R2.4: font clusters + class rollups + drift histogram."""
    typo = agg.get("typography", {})
    if not typo.get("fonts"):
        return ""
    head = "".join(f"<th>{h}</th>" for h in
                   ["Font", "Class", "Docs", "Words", "Median px", "p95 px", "Escalation",
                    "Top reason", "GPOS kern", "GSUB liga", "Subset"])
    rows = ""
    for f in typo["fonts"]:
        top_reason = max(f["reason_pct"], key=f["reason_pct"].get) if f["reason_pct"] else "—"
        flag = lambda v: "—" if v is None else ("✔" if v else "✖")  # noqa: E731
        rows += "<tr>" + "".join(f"<td>{c}</td>" for c in [
            escape(f["family"]), f["font_class"], f["documents"], f["words"],
            f["median_drift_px"], f["p95_drift_px"], f'{f["escalation_rate"]:.1%}',
            f'{escape(top_reason)} {f["reason_pct"].get(top_reason, 0)}%',
            flag(f["gpos_kerning"]), flag(f["gsub_ligatures"]), "✔" if f["subset_seen"] else "—",
        ]) + "</tr>"

    class_head = "".join(f"<th>{h}</th>" for h in ["Class", "Words", "Median px", "p95 px", "Escalation"])
    class_rows = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in [
            escape(cls), v["words"], v["median_drift_px"], v["p95_drift_px"], f'{v["escalation_rate"]:.1%}',
        ]) + "</tr>"
        for cls, v in typo.get("classes", {}).items()
    )
    hist = typo.get("drift_histogram", {})
    total = sum(hist.values()) or 1
    hist_rows = "".join(
        f'<tr><td>{escape(bucket)} px</td><td>{count}</td>'
        f'<td style="text-align:left">{"█" * max(1, round(40 * count / total)) if count else ""}</td></tr>'
        for bucket, count in hist.items()
    )
    return (
        '<div class="wrap"><h2>Typography clusters (per font)</h2>'
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
        '<h2>By font class</h2>'
        f'<div class="scroll"><table><thead><tr>{class_head}</tr></thead><tbody>{class_rows}</tbody></table></div>'
        '<h2>Drift distribution</h2>'
        f'<div class="scroll"><table><thead><tr><th>Bucket</th><th>Words</th><th></th></tr></thead>'
        f"<tbody>{hist_rows}</tbody></table></div></div>"
    )


def _quality_dashboard(env: dict, agg: dict, history: list[dict],
                       cat_html: str, cluster_html: str) -> str:
    fidelity = agg.get("fidelity", {})
    families = fidelity.get("families", {})
    total = agg.get("total", 0)
    critical = {"extraction", "typography", "layout", "rendering"}
    gauges = "".join(
        _gauge(name, stats.get("mean_score"),
               None if stats.get("documents_with_data", 0) == 0
               else stats.get("gate_passes", 0) == stats.get("documents_with_data", 0),
               name in critical)
        for name, stats in families.items()
    )
    cert = agg.get("certification", {})
    cert_tile = _gauge("Core v1 certification", None if not total else (1.0 if cert.get("certified") else 0.0),
                       cert.get("certified", False) if total else None, False)
    overall_tile = _gauge(f'Overall fidelity ({fidelity.get("overall_passes", 0)}/{total} docs)',
                          None, (fidelity.get("overall_passes", 0) == total) if total else None, False)
    provenance = " · ".join(f"{k}: {escape(str(v))}" for k, v in env.items() if k != "feature_flags")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>LayoutForge Quality Dashboard</title>
<style>{_DASH_STYLE}</style></head><body>
<header><h1>Quality Dashboard — Document Fidelity</h1><div class="prov">{provenance}</div></header>
<div class="tiles">{overall_tile}{cert_tile}{gauges}</div>
{_trend_table(history)}
{cat_html}
{cluster_html}
{_drift_section(agg)}
{_typography_section(agg)}
</body></html>
"""


def write_reports(
    out_dir: Path, env: dict, records: list[dict], compares: dict[str, dict],
    aggregates: dict, regressions: list[str], history: list[dict] | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "summary.json").write_text(
        json.dumps({"environment": env, "aggregates": aggregates, "regressions": regressions, "documents": records}, indent=2),
        encoding="utf-8",
    )

    with (out_dir / "metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["document", "ok", "pages", "chars_total", "chars_lost", "chars_substituted",
                         "paragraphs", "runs", "legacy_spans", "semantic_spans", "span_reduction",
                         "css_rules", "unicode_parity", "total_seconds"])
        for rec in records:
            cmp = compares.get(rec["name"], {})
            writer.writerow([
                rec["name"], rec["ok"], rec["pages"], rec["fidelity"]["chars_total"],
                rec["fidelity"]["chars_lost"], rec["fidelity"]["chars_substituted"],
                rec["structure"]["paragraphs"], rec["structure"]["runs"],
                rec["rendering"]["legacy_spans"], rec["rendering"]["semantic_spans"],
                rec["rendering"]["span_reduction"], rec["rendering"]["css_rules"],
                cmp.get("unicode_parity", ""), rec["performance"]["total_seconds"],
            ])

    (out_dir / "index.html").write_text(_dashboard(env, aggregates, records, compares, regressions), encoding="utf-8")

    # M-R2.4: the typography cluster report as its own machine-readable file
    # (fulfils M-R0's "typography report" family).
    if aggregates.get("typography"):
        (out_dir / "typography_report.json").write_text(
            json.dumps(aggregates["typography"], indent=2), encoding="utf-8")

    # M-R1: the human-readable quality dashboard — gauge cards per fidelity
    # family (gated, weakest-link scores), trends, categories, clusters,
    # certification. index.html stays the per-document detail report.
    (out_dir / "quality_dashboard.html").write_text(
        _quality_dashboard(env, aggregates, history or [],
                           _category_section(aggregates), _cluster_section(aggregates)),
        encoding="utf-8",
    )
