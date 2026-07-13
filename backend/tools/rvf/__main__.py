"""RVF CLI.

    python -m tools.rvf <corpus_dir> [--out DIR] [--baseline FILE]
                        [--update-baseline] [--dpi N]

Runs every *.pdf under <corpus_dir> through the pipeline, writes a report to
--out, and (with --baseline) compares against / updates a regression baseline.
Exit code is non-zero if any document failed or a regression was detected, so
it drops straight into CI.
"""

import argparse
import sys
from pathlib import Path

from tools.rvf.runner import run_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.rvf", description="Rendering Validation Framework")
    parser.add_argument("corpus_dir", type=Path, help="directory of PDFs (searched recursively)")
    parser.add_argument("--out", type=Path, default=Path("rvf_report"), help="report output directory")
    parser.add_argument("--baseline", type=Path, default=None, help="baseline JSON to compare/update")
    parser.add_argument("--update-baseline", action="store_true", help="overwrite the baseline with this run")
    parser.add_argument("--dpi", type=int, default=150, help="background render DPI (throughput vs fidelity)")
    args = parser.parse_args(argv)

    if not args.corpus_dir.exists():
        print(f"corpus directory not found: {args.corpus_dir}", file=sys.stderr)
        return 2

    result = run_corpus(
        args.corpus_dir, args.out,
        baseline_path=args.baseline, update_baseline=args.update_baseline, dpi=args.dpi,
    )
    agg = result.aggregates
    cert = agg.get("certification", {})
    sev = agg.get("issues_by_severity", {})
    print(
        f"\n{agg['ok']}/{agg['total']} ok · unicode {agg['unicode_fidelity_pct']:.4f}% · "
        f"lost {agg['chars_lost']} · parity fails {agg['unicode_parity_failures']} · "
        f"span reduction {agg['span_reduction']:,} · {agg['total_seconds']:.1f}s"
    )
    print(
        f"issues: {agg.get('total_issues', 0)} "
        f"(P0={sev.get('P0', 0)} P1={sev.get('P1', 0)} P2={sev.get('P2', 0)} P3={sev.get('P3', 0)}) · "
        f"Core v1: {'CERTIFIED' if cert.get('certified') else 'NOT CERTIFIED'}"
    )
    print(f"report: {(args.out / 'index.html').resolve()}")
    if result.regressions:
        print("\nREGRESSIONS:")
        for line in result.regressions:
            print(f"  - {line}")

    return 1 if (agg["failed"] or result.regressions) else 0


if __name__ == "__main__":
    raise SystemExit(main())
