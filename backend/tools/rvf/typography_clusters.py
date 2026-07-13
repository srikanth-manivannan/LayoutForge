"""Typography Cluster Analysis (M-R2.4 — investigation only, NO engine changes).

One corpus-level report that makes M-R3 evidence-driven:

- per-FONT clusters: documents, words, median/p95 drift, escalation rate,
  reason breakdown (%), and OpenType capabilities probed from the actual
  extracted font file (kern table / GPOS kern feature / GSUB liga feature) —
  the direct test of "real kerning vs width-table mismatch";
- per-CLASS rollups (handwriting / serif / sans / display / typewriter /
  unknown) — does LayoutForge struggle with classes of typography?;
- drift + escalation HISTOGRAMS (a distribution tells a richer story than a
  median);
- worst fonts / most stable fonts.

Class assignment is a name heuristic and says so (`class_source:
"name_heuristic"`) — good enough to spot class-level patterns, replaced by
real classification data when the Typography Knowledge Base (M-R2.5) lands.
"""

import io
from collections import defaultdict
from pathlib import Path
from statistics import median

from fontTools.ttLib import TTFont

from app.pipeline.document import Document

DRIFT_BINS = (0.1, 0.2, 0.5, 1.0)  # px → buckets 0–0.1, 0.1–0.2, 0.2–0.5, 0.5–1, >1

_CLASS_TOKENS = {
    "handwriting": ("hand", "script", "brush", "ink", "chauncy", "dancing", "comic",
                    "marker", "crayon", "kids", "kg", "schoolbell", "kristen"),
    "typewriter": ("courier", "mono", "consol", "typewriter", "prestige"),
    "serif": ("times", "palatino", "georgia", "garamond", "minion", "caslon",
              "baskerville", "book", "roman", "serif", "century", "charter"),
    "sans": ("helvetica", "arial", "avenir", "futura", "gotham", "verdana",
             "tahoma", "calibri", "lato", "roboto", "grande", "franklin", "gill"),
    "display": ("display", "poster", "impact", "cooper", "bauhaus", "stencil"),
}


def classify_font_class(family: str) -> str:
    lowered = family.lower()
    for cls, tokens in _CLASS_TOKENS.items():
        if any(token in lowered for token in tokens):
            return cls
    return "unknown"


def probe_font_capabilities(font_path: Path) -> dict:
    """OpenType layout capabilities of an extracted font FILE — evidence for
    whether residual drift can be real kerning/ligatures at all."""
    try:
        font = TTFont(io.BytesIO(font_path.read_bytes()), lazy=True)
    except Exception:  # noqa: BLE001 - unreadable file → honest unknowns
        return {"readable": False}

    def feature_tags(table_tag: str) -> set:
        try:
            table = font[table_tag].table
            return {fr.FeatureTag for fr in table.FeatureList.FeatureRecord}
        except Exception:  # noqa: BLE001
            return set()

    gpos = feature_tags("GPOS") if "GPOS" in font else set()
    gsub = feature_tags("GSUB") if "GSUB" in font else set()
    return {
        "readable": True,
        "has_kern_table": "kern" in font,
        "has_gpos_kerning": "kern" in gpos,
        "has_gsub_ligatures": bool({"liga", "dlig", "rlig", "clig"} & gsub),
        "glyph_count": font["maxp"].numGlyphs if "maxp" in font else None,
    }


def histogram(values: list[float], bins: tuple = DRIFT_BINS) -> dict:
    labels = [f"0-{bins[0]}"] + [f"{a}-{b}" for a, b in zip(bins, bins[1:])] + [f">{bins[-1]}"]
    counts = [0] * (len(bins) + 1)
    for value in values:
        for index, edge in enumerate(bins):
            if value <= edge:
                counts[index] += 1
                break
        else:
            counts[-1] += 1
    return dict(zip(labels, counts))


def _percentile(ordered: list[float], fraction: float) -> float:
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def analyze_document_fonts(document: Document, project_dir: Path | None) -> list[dict]:
    """Per-font observation rows for ONE document (raw material for the
    corpus aggregation)."""
    fonts_dir = Path(project_dir) / "resources" / "fonts" if project_dir else None
    rows = []
    by_font_words: dict[str, list] = defaultdict(list)
    font_meta = {font.id: font for font in document.fonts}

    for page in document.pages:
        for block in page.text_blocks:
            for word in block.words:
                if word.text.strip():
                    by_font_words[word.font_id or ""].append(word)

    for font_id, words in by_font_words.items():
        font = font_meta.get(font_id)
        family = font.family if font else "unknown"
        capabilities = {}
        if font is not None and font.filename and fonts_dir is not None:
            capabilities = probe_font_capabilities(fonts_dir / font.filename)
        drifts = [abs(word.width_error) for word in words]
        reasons: dict[str, int] = defaultdict(int)
        for word in words:
            reasons[word.reason] += 1
        rows.append({
            "family": family,
            "font_class": classify_font_class(family),
            "class_source": "name_heuristic",
            "subset": bool(font and font.subset),
            "words": len(words),
            "drifts": drifts,  # raw — dropped at aggregation
            "escalated": sum(1 for word in words if word.mode == "glyph"),
            "reasons": dict(reasons),
            "capabilities": capabilities,
        })
    return rows


def aggregate_typography(rows_per_document: list[list[dict]]) -> dict:
    """The corpus report: font clusters, class rollups, histograms,
    worst/most-stable fonts."""
    fonts: dict[str, dict] = {}
    for document_rows in rows_per_document:
        for row in document_rows:
            slot = fonts.setdefault(row["family"], {
                "family": row["family"], "font_class": row["font_class"],
                "class_source": row["class_source"], "documents": 0, "words": 0,
                "escalated": 0, "drifts": [], "reasons": defaultdict(int),
                "subset_seen": False, "capabilities": {},
            })
            slot["documents"] += 1
            slot["words"] += row["words"]
            slot["escalated"] += row["escalated"]
            slot["drifts"].extend(row["drifts"])
            slot["subset_seen"] = slot["subset_seen"] or row["subset"]
            for reason, count in row["reasons"].items():
                slot["reasons"][reason] += count
            if row["capabilities"].get("readable"):
                slot["capabilities"] = row["capabilities"]

    font_rows = []
    class_drifts: dict[str, list[float]] = defaultdict(list)
    class_words: dict[str, int] = defaultdict(int)
    class_escalated: dict[str, int] = defaultdict(int)
    all_drifts: list[float] = []
    escalation_rates: list[float] = []

    for slot in fonts.values():
        ordered = sorted(slot["drifts"])
        total_reasons = sum(slot["reasons"].values()) or 1
        escalation = slot["escalated"] / slot["words"] if slot["words"] else 0.0
        caps = slot["capabilities"]
        font_rows.append({
            "family": slot["family"],
            "font_class": slot["font_class"],
            "documents": slot["documents"],
            "words": slot["words"],
            "median_drift_px": round(median(ordered), 3) if ordered else 0.0,
            "p95_drift_px": round(_percentile(ordered, 0.95), 3),
            "escalation_rate": round(escalation, 4),
            "reason_pct": {r: round(100 * n / total_reasons, 1) for r, n in slot["reasons"].items()},
            "subset_seen": slot["subset_seen"],
            "gpos_kerning": caps.get("has_gpos_kerning"),
            "kern_table": caps.get("has_kern_table"),
            "gsub_ligatures": caps.get("has_gsub_ligatures"),
        })
        class_drifts[slot["font_class"]].extend(slot["drifts"])
        class_words[slot["font_class"]] += slot["words"]
        class_escalated[slot["font_class"]] += slot["escalated"]
        all_drifts.extend(slot["drifts"])
        escalation_rates.append(escalation)

    font_rows.sort(key=lambda r: -r["median_drift_px"])
    classes = {}
    for cls, drifts in sorted(class_drifts.items()):
        ordered = sorted(drifts)
        classes[cls] = {
            "words": class_words[cls],
            "median_drift_px": round(median(ordered), 3) if ordered else 0.0,
            "p95_drift_px": round(_percentile(ordered, 0.95), 3),
            "escalation_rate": round(class_escalated[cls] / class_words[cls], 4) if class_words[cls] else 0.0,
        }

    measurable = [r for r in font_rows if r["words"] >= 20]  # thin data ≠ evidence
    return {
        "fonts": font_rows,
        "classes": classes,
        "drift_histogram": histogram(all_drifts),
        "escalation_histogram": histogram(escalation_rates, bins=(0.05, 0.1, 0.25, 0.5)),
        "gpos_candidates": [r["family"] for r in font_rows if r["gpos_kerning"] or r["kern_table"]],
        "gsub_candidates": [r["family"] for r in font_rows if r["gsub_ligatures"]],
        "worst_fonts": [r["family"] for r in measurable[:5]],
        "most_stable_fonts": [r["family"] for r in sorted(measurable, key=lambda r: r["median_drift_px"])[:5]],
    }
