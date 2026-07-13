"""Drift diagnostics (M-R2a, approval condition for Typography Measurement
Engine v2).

Per-document drift statistics at the three granularities that matter for
verifying M-R2 improves the RIGHT parts of the system:

- per PAGE     — mean / median / p95 / max drift + the worst words
- per FONT     — is one font engine broken, or the general algorithm?
- per REASON   — which ReconstructionReason carries the error, and how much
                 each contributes to total drift

"Drift" here = |width_error| per word (the same quantity fidelity's
word_drift_px summarizes) — bbox-vs-advance based before M-R2b, residual
after-fit based once advance measurement lands, so these reports double as
the before/after evidence for the milestone.
"""

from collections import defaultdict
from statistics import mean, median

from app.pipeline.document import Document

WORST_WORDS_LIMIT = 20


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, int(len(sorted_values) * fraction))
    return sorted_values[index]


def _stats(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "mean": round(mean(ordered), 3) if ordered else 0.0,
        "median": round(median(ordered), 3) if ordered else 0.0,
        "p95": round(_percentile(ordered, 0.95), 3),
        "max": round(ordered[-1], 3) if ordered else 0.0,
    }


def drift_report(document: Document) -> dict:
    """The full per-page / per-font / per-reason drift breakdown for one
    document, plus the worst offending words overall."""
    font_family = {font.id: font.family for font in document.fonts}

    by_page: dict[int, list[float]] = defaultdict(list)
    by_font: dict[str, list[float]] = defaultdict(list)
    by_reason: dict[str, list[float]] = defaultdict(list)
    words: list[dict] = []
    total_drift = 0.0

    for page in document.pages:
        for block in page.text_blocks:
            for word in block.words:
                if not word.text.strip():
                    continue
                drift = abs(word.width_error)
                total_drift += drift
                by_page[page.number].append(drift)
                by_font[font_family.get(word.font_id or "", "unknown")].append(drift)
                by_reason[word.reason].append(drift)
                words.append({
                    "page": page.number,
                    "text": word.text[:40],
                    "font": font_family.get(word.font_id or "", "unknown"),
                    "reason": word.reason,
                    "mode": word.mode,
                    "drift_px": round(drift, 3),
                })

    words.sort(key=lambda w: -w["drift_px"])
    reasons = {}
    for reason, values in by_reason.items():
        stats = _stats(values)
        stats["contribution_pct"] = round(100.0 * sum(values) / total_drift, 1) if total_drift else 0.0
        reasons[reason] = stats

    return {
        "overall": _stats([w["drift_px"] for w in words]),
        "by_page": {str(number): _stats(values) for number, values in sorted(by_page.items())},
        "by_font": {family: _stats(values) for family, values in sorted(by_font.items())},
        "by_reason": reasons,
        "worst_words": words[:WORST_WORDS_LIMIT],
    }


def aggregate_drift(reports: list[dict]) -> dict:
    """Corpus-level rollup: per-font and per-reason across every document —
    the 'one font engine vs the general algorithm' answer."""
    font_values: dict[str, list[float]] = defaultdict(list)
    reason_values: dict[str, list[float]] = defaultdict(list)
    for report in reports:
        for family, stats in report.get("by_font", {}).items():
            # mean×count reconstructs the sum without shipping raw values.
            font_values[family].extend([stats["mean"]] * stats["count"])
        for reason, stats in report.get("by_reason", {}).items():
            reason_values[reason].extend([stats["mean"]] * stats["count"])
    total = sum(sum(v) for v in reason_values.values())
    reasons = {}
    for reason, values in reason_values.items():
        stats = _stats(values)
        stats["contribution_pct"] = round(100.0 * sum(values) / total, 1) if total else 0.0
        reasons[reason] = stats
    return {
        "by_font": {family: _stats(values) for family, values in sorted(font_values.items())},
        "by_reason": reasons,
    }
