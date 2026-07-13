"""M-R0 Benchmark & Certification Platform: category derivation, per-category
aggregates, failure clustering with the significance rule, extraction-accuracy
metrics, and the corpus-relative-name collision fix."""

from pathlib import Path

from tools.rvf.clusters import build_clusters
from tools.rvf.runner import category_of, run_corpus
from tests.conftest import make_rich_pdf_bytes


def _issue(code: str, stage: str = "word_builder", severity: str = "P2") -> dict:
    return {"code": code, "stage": stage, "severity": severity, "category": "Typography"}


# ---- clustering + significance rule ----------------------------------------

def test_cluster_groups_by_code_and_stage_across_documents() -> None:
    issues_by_doc = {
        "novels/a.pdf": [_issue("empty_run")],
        "novels/b.pdf": [_issue("empty_run")],
        "comics/c.pdf": [_issue("empty_run"), _issue("character_loss", "extraction", "P0")],
    }
    cats = {"novels/a.pdf": "novels", "novels/b.pdf": "novels", "comics/c.pdf": "comics"}
    clusters = build_clusters(issues_by_doc, cats, {"novels": 2, "comics": 1})
    by_code = {c["code"]: c for c in clusters}
    assert by_code["empty_run"]["document_count"] == 3
    assert by_code["empty_run"]["categories"] == ["comics", "novels"]
    assert by_code["empty_run"]["significant"] is True  # >= 3 docs
    # P0 cluster sorts first even with fewer documents.
    assert clusters[0]["code"] == "character_loss"


def test_category_fraction_triggers_significance() -> None:
    # 1 doc out of a 4-doc category = 25% >= 20% threshold.
    issues_by_doc = {"math/m1.pdf": [_issue("baseline_inversion", "reading_order", "P3")]}
    clusters = build_clusters(issues_by_doc, {"math/m1.pdf": "math"}, {"math": 4})
    assert clusters[0]["max_category_fraction"] == 0.25
    assert clusters[0]["significant"] is True


def test_isolated_issue_is_not_significant() -> None:
    # 1 doc in a 10-doc category (10% < 20%), fewer than 3 docs.
    issues_by_doc = {"novels/n1.pdf": [_issue("empty_run")]}
    clusters = build_clusters(issues_by_doc, {"novels/n1.pdf": "novels"}, {"novels": 10})
    assert clusters[0]["significant"] is False


# ---- category derivation ----------------------------------------------------

def test_category_is_first_directory_under_corpus_root(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    (corpus / "novels").mkdir(parents=True)
    nested = corpus / "novels" / "series" / "x.pdf"
    assert category_of(corpus / "novels" / "a.pdf", corpus) == "novels"
    assert category_of(nested, corpus) == "novels"
    assert category_of(corpus / "root.pdf", corpus) == "uncategorized"


# ---- end-to-end: categories, clusters, extraction metrics, collision fix ----

def test_corpus_run_produces_category_rows_clusters_and_distinct_artifacts(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    for cat in ("Publishing", "Academic"):
        (corpus / cat).mkdir(parents=True)
        # SAME filename in both categories — must not collide anywhere.
        (corpus / cat / "doc.pdf").write_bytes(make_rich_pdf_bytes(pages=2))

    result = run_corpus(corpus, tmp_path / "report")
    agg = result.aggregates

    # Per-category aggregates exist and each saw exactly one document.
    assert set(agg["by_category"]) == {"Academic", "Publishing"}
    assert all(v["documents"] == 1 and v["ok"] == 1 for v in agg["by_category"].values())

    # Records are keyed by corpus-relative path, not bare filename.
    names = {r["name"] for r in result.records}
    assert names == {"Academic/doc.pdf", "Publishing/doc.pdf"}

    # Artifact directories are distinct (collision regression test).
    doc_dirs = sorted(p.name for p in (tmp_path / "report" / "documents").iterdir())
    assert len(doc_dirs) == 2 and doc_dirs[0] != doc_dirs[1]

    # Clusters key present (empty list is fine for a clean corpus).
    assert isinstance(agg["clusters"], list)

    # Extraction Accuracy family present per document.
    for record in result.records:
        extraction = record["extraction"]
        assert extraction["chars_total"] > 0
        assert extraction["fonts_total"] >= 1
        assert "shapes_total" in extraction  # 0 until M-R8 — visible gap
