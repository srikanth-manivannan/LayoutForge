"""Rich IDM validator (Phase 2.5).

Pure, renderer-agnostic checks over the Document tree. Returns a flat list of
Violations; the caller decides policy (report vs gate). Error-severity
violations mean the model is not safe to render semantically; warnings are
suspicious but non-fatal.
"""

from collections import Counter
from dataclasses import dataclass

from app.pipeline.document import Document
from app.pipeline.elements.page import Page

_BASELINE_TOLERANCE = 1.0  # px; lines may share a baseline within this


@dataclass(frozen=True)
class Violation:
    code: str
    severity: str  # "error" | "warning"
    page: int
    node_id: str
    message: str

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "page": self.page,
            "node_id": self.node_id,
            "message": self.message,
        }


def validate_document(document: Document) -> list[Violation]:
    font_ids = {font.id for font in document.fonts}
    violations: list[Violation] = []
    for page in document.pages:
        violations.extend(_validate_page(page, font_ids))
    return violations


def _validate_page(page: Page, font_ids: set[str]) -> list[Violation]:
    out: list[Violation] = []
    seen_ids: set[str] = set()

    def check_id(node_id: str) -> None:
        if node_id in seen_ids:
            out.append(Violation("duplicate_node_id", "error", page.number, node_id, "id used more than once on the page"))
        seen_ids.add(node_id)

    for region in page.regions:
        check_id(region.id)
        for paragraph in region.paragraphs:
            check_id(paragraph.id)
            if not paragraph.lines:
                out.append(Violation("paragraph_without_lines", "error", page.number, paragraph.id, "paragraph has no lines"))
            _check_baseline_order(page.number, paragraph, out)
            for line in paragraph.lines:
                check_id(line.id)
                if not line.runs:
                    out.append(Violation("line_without_runs", "error", page.number, line.id, "line has no runs"))
                run_text_by_id: dict[str, str] = {}
                for run in line.runs:
                    check_id(run.id)
                    run_text_by_id[run.id] = run.text
                    if run.text == "":
                        out.append(Violation("empty_run", "error", page.number, run.id, "run carries no text"))
                    if run.font_id and run.font_id not in font_ids:
                        out.append(Violation("invalid_font_reference", "error", page.number, run.id, f"run references unknown font {run.font_id}"))
                _check_words(page.number, line, run_text_by_id, out, check_id)

    out.extend(_check_character_fidelity(page))
    return out


def _check_words(page_number, line, run_text_by_id, out, check_id) -> None:
    """Lexical integrity (Phase 2.6): every word is fragment-reconstructed
    from the line's runs, fragments reassemble the word exactly, and every
    non-whitespace run is covered by some word (no lexical gap)."""
    referenced: set[str] = set()
    for word in line.words:
        check_id(word.id)
        if not word.fragments:
            out.append(Violation("word_without_run", "error", page_number, word.id, f"word {word.text!r} has no fragments"))
            continue
        if "".join(f.text for f in word.fragments) != word.text:
            out.append(Violation("word_fragment_mismatch", "error", page_number, word.id, f"fragments do not reassemble {word.text!r}"))
        for fragment in word.fragments:
            referenced.add(fragment.run_id)
            if fragment.run_id not in run_text_by_id:
                out.append(Violation("fragment_foreign_run", "error", page_number, word.id, f"fragment references run {fragment.run_id} not on this line"))
            elif fragment.text not in run_text_by_id[fragment.run_id]:
                out.append(Violation("fragment_text_not_in_run", "error", page_number, word.id, f"fragment {fragment.text!r} is not in its run"))
    for run_id, text in run_text_by_id.items():
        if text.strip() and run_id not in referenced:
            out.append(Violation("run_without_word", "error", page_number, run_id, "run has text but no word references it"))


def _check_baseline_order(page_number: int, paragraph, out: list[Violation]) -> None:
    prev = None
    for line in paragraph.lines:
        if prev is not None and line.baseline_y < prev - _BASELINE_TOLERANCE:
            out.append(Violation(
                "baseline_inversion", "warning", page_number, line.id,
                f"line baseline {line.baseline_y:.1f} is above the previous line {prev:.1f}",
            ))
        prev = line.baseline_y


def _check_character_fidelity(page: Page) -> list[Violation]:
    """The tree must carry every character the extracted lines carried
    (gate 0, ADR-010). Compared as a character multiset."""
    legacy = Counter("".join(block.text for block in page.text_blocks))
    tree = Counter(
        "".join(
            run.text
            for region in page.regions
            for paragraph in region.paragraphs
            for line in paragraph.lines
            for run in line.runs
        )
    )
    lost = legacy - tree
    if not lost:
        return []
    return [Violation(
        "character_loss", "error", page.number, f"page-{page.number}",
        f"tree is missing {sum(lost.values())} character(s): {dict(list(lost.items())[:8])}",
    )]


def summarize(violations: list[Violation]) -> dict:
    by_code: dict[str, int] = {}
    errors = warnings = 0
    for v in violations:
        by_code[v.code] = by_code.get(v.code, 0) + 1
        if v.severity == "error":
            errors += 1
        else:
            warnings += 1
    return {
        "errors": errors,
        "warnings": warnings,
        "by_code": by_code,
        # Cap the stored detail so a badly-broken document can't bloat idm.json.
        "violations": [v.to_dict() for v in violations[:200]],
    }
