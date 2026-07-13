"""Fidelity + writer diff (RVF).

The authoritative check is **semantic HTML ↔ IDM tree**: extraction is the
source of truth (strict pipeline, ADR-011), so the semantic writer's output
must carry exactly the tree's characters. The legacy writer is the thing being
*replaced* and carries its own artifacts (e.g. \\ufeff word joiners), so it is
NOT the fidelity oracle — it contributes only the span-count reduction story
(collected in metrics). Zero-width formatting marks are ignored as non-content.
"""

from tools.rvf.metrics import html_text, nonspace
from tools.rvf.pipeline import RunArtifacts

_ZERO_WIDTH = str.maketrans({c: None for c in "﻿​‌‍⁠"})


def _clean(text: str) -> str:
    return nonspace(text).translate(_ZERO_WIDTH)


def _page_tree_text(page) -> str:
    return "".join(
        run.text
        for region in page.regions
        for paragraph in region.paragraphs
        for line in paragraph.lines
        for run in line.runs
    )


def compare(art: RunArtifacts) -> dict:
    if not art.ok or art.document is None or art.project_dir is None:
        return {"comparable": False}
    semantic_dir = art.project_dir / "pages_semantic"
    if not semantic_dir.exists():
        return {"comparable": False}

    mismatched_pages = 0
    mismatch_chars = 0
    compared = 0
    for page in art.document.pages:
        html_file = semantic_dir / f"page_{page.number:04d}.html"
        if not html_file.exists():
            continue
        compared += 1
        tree_text = _clean(_page_tree_text(page))
        rendered = _clean(html_text(html_file.read_text(encoding="utf-8")))
        if tree_text != rendered:
            mismatched_pages += 1
            mismatch_chars += abs(len(tree_text) - len(rendered))

    return {
        "comparable": True,
        "pages_compared": compared,
        "unicode_mismatched_pages": mismatched_pages,
        "unicode_mismatch_chars": mismatch_chars,
        "unicode_parity": mismatched_pages == 0,
    }
