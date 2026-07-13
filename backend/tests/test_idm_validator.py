"""Rich IDM validator (Phase 2.5): rejects internally-inconsistent models so
the renderer only ever compiles a valid tree."""

from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.line import Line
from app.pipeline.elements.page import Page
from app.pipeline.elements.paragraph import Paragraph
from app.pipeline.elements.region import Region
from app.pipeline.elements.run import Run
from app.pipeline.elements.textbox import TextBlock
from app.pipeline.elements.word import Word, WordFragment
from app.pipeline.validation.idm_validator import summarize, validate_document

BB = BoundingBox(0, 0, 100, 12)


def _run(text: str, rid: str = "r", font_id: str = "f1") -> Run:
    return Run(id=rid, bbox=BB, text=text, font_id=font_id, font_size=12.0)


def _word(text: str, run_id: str, wid: str = "w") -> Word:
    return Word(id=wid, text=text, bbox=BB, fragments=[WordFragment(run_id, text)])


def _para(lines: list[Line], pid: str = "p") -> Paragraph:
    return Paragraph(id=pid, bbox=BB, lines=lines)


def _line(runs: list[Run], lid: str = "l", baseline: float = 10.0, words: list[Word] | None = None) -> Line:
    return Line(id=lid, bbox=BB, baseline_y=baseline, runs=runs, words=words or [])


def _doc(page: Page, fonts: list[FontResource] | None = None) -> Document:
    return Document(project_id="p", pages=[page], fonts=fonts or [FontResource(id="f1", original_name="Arial", family="Arial")])


def _codes(page: Page, fonts=None) -> set[str]:
    return {v.code for v in validate_document(_doc(page, fonts))}


def test_clean_tree_has_no_violations() -> None:
    line = _line([_run("Hello world")], words=[_word("Hello", "r"), _word("world", "r", "w2")])
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="Hello world")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert validate_document(_doc(page)) == []


def test_mixed_style_word_spanning_runs_is_valid() -> None:
    # "theToad": one word, fragments across two runs — legal, not a crossing.
    runs = [_run("the", rid="r1"), _run("Toad", rid="r2")]
    word = Word(id="w", text="theToad", bbox=BB, fragments=[WordFragment("r1", "the"), WordFragment("r2", "Toad")])
    line = _line(runs, words=[word])
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="theToad")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert validate_document(_doc(page)) == []


def test_fragment_text_not_in_run_is_flagged() -> None:
    # A fragment claims text its run does not contain → integrity error.
    line = _line([_run("New York Time")], words=[_word("Times", "r")])
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="New York Time")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert "fragment_text_not_in_run" in _codes(page)


def test_word_fragment_mismatch_is_flagged() -> None:
    word = Word(id="w", text="Times", bbox=BB, fragments=[WordFragment("r", "Time"), WordFragment("r", "x")])
    line = _line([_run("Timex")], words=[word])
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="Timex")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert "word_fragment_mismatch" in _codes(page)


def test_run_without_word_is_flagged() -> None:
    # A run with real text that no word covers is a lexical gap.
    line = _line([_run("orphan")], words=[])
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="orphan")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert "run_without_word" in _codes(page)


def test_empty_and_childless_nodes_flagged() -> None:
    page = Page(number=1, width=200, height=200,
                regions=[Region(id="reg", bbox=BB, paragraphs=[
                    _para([]),  # paragraph without lines
                    _para([_line([])], pid="p2"),  # line without runs
                    _para([_line([_run("")], lid="l3")], pid="p3"),  # empty run
                ])])
    codes = _codes(page)
    assert {"paragraph_without_lines", "line_without_runs", "empty_run"} <= codes


def test_invalid_font_reference_flagged() -> None:
    line = _line([_run("hi", font_id="ghost")])
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="hi")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert "invalid_font_reference" in _codes(page)


def test_baseline_inversion_flagged_as_warning() -> None:
    lines = [_line([_run("a")], lid="l1", baseline=100.0), _line([_run("b")], lid="l2", baseline=40.0)]
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="ab")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para(lines)])])
    violations = validate_document(_doc(page))
    assert any(v.code == "baseline_inversion" and v.severity == "warning" for v in violations)


def test_character_loss_flagged() -> None:
    line = _line([_run("ab")])  # tree has "ab"
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="abc")],  # legacy had "abc"
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert "character_loss" in _codes(page)


def test_duplicate_node_id_flagged() -> None:
    line = _line([_run("a", rid="dup"), _run("b", rid="dup")])
    page = Page(number=1, width=200, height=200,
                text_blocks=[TextBlock(id="b", page=1, bbox=BB, text="ab")],
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([line])])])
    assert "duplicate_node_id" in _codes(page)


def test_summarize_counts_by_severity_and_code() -> None:
    page = Page(number=1, width=200, height=200,
                regions=[Region(id="reg", bbox=BB, paragraphs=[_para([])])])
    summary = summarize(validate_document(_doc(page)))
    assert summary["errors"] >= 1
    assert "paragraph_without_lines" in summary["by_code"]
