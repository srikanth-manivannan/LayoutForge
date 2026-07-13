"""Failure clustering (RVF, M-R0 Benchmark Platform).

Groups every document's issues by (code, earliest stage) into corpus-level
clusters with document and category coverage — so "affects N docs across M
categories" is computed, never guessed, and the Development-Model cluster
rule (a fix targets a cluster of ≥3 documents or ≥20% of a category) is
machine-evaluated instead of judged by hand.
"""

from collections import defaultdict

# The binding significance rule (docs/RENDERING_RECOVERY_ROADMAP.md): a
# cluster is worth engineering effort when it spans at least this many
# documents, or covers at least this fraction of any single category.
MIN_CLUSTER_DOCS = 3
MIN_CATEGORY_FRACTION = 0.20

_SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def build_clusters(
    issues_by_document: dict[str, list[dict]],
    category_by_document: dict[str, str],
    docs_per_category: dict[str, int],
) -> list[dict]:
    """`issues_by_document` maps corpus-relative document name → its
    classified issues. Returns clusters sorted most-severe, then widest."""
    grouped: dict[tuple[str, str], dict] = {}
    for doc_name, issues in issues_by_document.items():
        category = category_by_document.get(doc_name, "uncategorized")
        for issue in issues:
            key = (issue["code"], issue["stage"])
            cluster = grouped.setdefault(key, {
                "code": issue["code"],
                "stage": issue["stage"],
                "category": issue["category"],
                "severity": issue["severity"],
                "documents": set(),
                "categories": set(),
                "occurrences": 0,
            })
            cluster["documents"].add(doc_name)
            cluster["categories"].add(category)
            cluster["occurrences"] += 1
            if _SEVERITY_RANK.get(issue["severity"], 9) < _SEVERITY_RANK.get(cluster["severity"], 9):
                cluster["severity"] = issue["severity"]

    per_category_hits: dict[tuple[str, str, str], set] = defaultdict(set)
    for doc_name, issues in issues_by_document.items():
        category = category_by_document.get(doc_name, "uncategorized")
        for issue in issues:
            per_category_hits[(issue["code"], issue["stage"], category)].add(doc_name)

    clusters: list[dict] = []
    for (code, stage), cluster in grouped.items():
        max_category_fraction = 0.0
        for category in cluster["categories"]:
            total = docs_per_category.get(category, 0)
            if total:
                hits = len(per_category_hits[(code, stage, category)])
                max_category_fraction = max(max_category_fraction, hits / total)
        significant = (
            len(cluster["documents"]) >= MIN_CLUSTER_DOCS
            or max_category_fraction >= MIN_CATEGORY_FRACTION
        )
        clusters.append({
            "code": code,
            "stage": stage,
            "category": cluster["category"],
            "severity": cluster["severity"],
            "document_count": len(cluster["documents"]),
            "documents": sorted(cluster["documents"])[:20],
            "categories": sorted(cluster["categories"]),
            "occurrences": cluster["occurrences"],
            "max_category_fraction": round(max_category_fraction, 3),
            "significant": significant,
        })

    clusters.sort(key=lambda c: (_SEVERITY_RANK.get(c["severity"], 9), -c["document_count"]))
    return clusters
