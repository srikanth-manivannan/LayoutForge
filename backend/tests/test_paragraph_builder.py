"""Paragraph Builder (Phase 2): weighted-evidence grouping with explainable
confidence + signals. Lines that share rhythm/edge/font cohere; a big
baseline gap or a font-size jump breaks the paragraph."""

import uuid

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.line import Line
from app.pipeline.elements.run import Run
from app.pipeline.typography.paragraph_builder import build_paragraphs


def _line(baseline_y: float, x: float = 0.0, width: float = 400.0, size: float = 10.0,
          leading: float = 12.0, font_id: str = "f1", text: str = "lorem ipsum dolor") -> Line:
    run = Run(
        id=str(uuid.uuid4()),
        bbox=BoundingBox(x=x, y=baseline_y - size, width=width, height=size),
        text=text,
        font_id=font_id,
        font_size=size,
        color="#000000",
    )
    return Line(
        id=str(uuid.uuid4()),
        bbox=BoundingBox(x=x, y=baseline_y - size, width=width, height=size),
        baseline_y=baseline_y,
        leading=leading,
        runs=[run],
    )


def test_rhythmic_same_style_lines_merge_into_one_paragraph() -> None:
    lines = [_line(100.0), _line(112.0), _line(124.0)]  # exact 12px rhythm, aligned
    paras = build_paragraphs(lines)
    assert len(paras) == 1
    assert len(paras[0].lines) == 3
    assert paras[0].confidence >= 0.7
    assert "baseline" in paras[0].signals and "font" in paras[0].signals


def test_large_baseline_gap_breaks_paragraph() -> None:
    lines = [_line(100.0), _line(112.0), _line(160.0)]  # third line 48px below → break
    paras = build_paragraphs(lines)
    assert len(paras) == 2
    assert [len(p.lines) for p in paras] == [2, 1]


def test_font_size_jump_breaks_paragraph() -> None:
    heading = _line(100.0, size=24.0, leading=28.0, text="A Heading")
    body = [_line(140.0), _line(152.0)]
    paras = build_paragraphs([heading, *body])
    assert len(paras) == 2
    assert paras[0].lines[0].runs[0].text == "A Heading"


def test_line_height_uses_measured_baseline_gap_not_font_metric_estimate() -> None:
    """Reproduces the real-book finding (2026-07-14): a font's per-line
    ascender/descender ESTIMATE (Line.leading) can overstate the PDF's true
    inter-line spacing. When real consecutive baselines are available,
    Paragraph.line_height must reflect the MEASURED 14.4px gap, not the
    19.86px estimate every line individually carries — using the estimate
    silently inflates the paragraph's flowed height in the browser and
    pushes every following paragraph down the page."""
    lines = [_line(100.0, leading=19.86), _line(114.4, leading=19.86), _line(128.8, leading=19.86)]
    paras = build_paragraphs(lines)
    assert len(paras) == 1
    assert paras[0].line_height == 14.4  # measured, not the 19.86 estimate


def test_single_line_paragraph_falls_back_to_font_metric_estimate() -> None:
    """No real inter-line gap exists to measure for a lone line — the
    font-metric estimate is the only geometry available, and using it is
    not "inventing" data (Rule 4 concerns a later stage overriding an
    EARLIER stage's real measurement; here there is none to override)."""
    paras = build_paragraphs([_line(100.0, leading=19.86)])
    assert len(paras) == 1
    assert paras[0].line_height == 19.86


def test_hyphenation_holds_a_paragraph_together() -> None:
    # A slightly-too-large gap that would otherwise be borderline, rescued by
    # a trailing hyphen signalling the word continues on the next line.
    lines = [_line(100.0, text="continu-"), _line(115.0, text="ation here")]
    paras = build_paragraphs(lines)
    assert len(paras) == 1
    assert "hyphen" in paras[0].signals


def test_single_line_paragraph_is_confident_and_unflagged() -> None:
    paras = build_paragraphs([_line(100.0)])
    assert len(paras) == 1
    assert paras[0].reason == "single_line"
    assert paras[0].confidence == 1.0
