"""Base-14 handling: non-embedded standard fonts (Times/Helvetica/Courier)
must get metric-compatible CSS stacks AND real advances for width fitting —
they were previously skipped entirely, so every line in a base-14 PDF
rendered in generic sans-serif with uncorrected width (user-reported
"layout fully broken" on two real documents)."""

from app.pipeline.elements.font import FontResource
from app.pipeline.outputs.font_naming import css_family_stack
from app.pipeline.stages.normalize_idm import base14_metrics_for, natural_text_width


def _font(family: str, weight: str = "normal", style: str = "normal") -> FontResource:
    return FontResource(id="f1", original_name=family, family=family, weight=weight, style=style, filename=None)


def test_css_stack_maps_standard_fonts_to_metric_compatible_locals() -> None:
    assert '"Times New Roman", Times, serif' in css_family_stack(_font("Times-Roman"))
    assert "Arial, Helvetica, sans-serif" in css_family_stack(_font("Helvetica"))
    assert '"Courier New", Courier, monospace' in css_family_stack(_font("Courier"))
    # Unknown non-embedded families still fall back to generic sans.
    assert css_family_stack(_font("SomeCustomFont")).endswith("sans-serif")


def test_base14_metrics_measure_real_advances() -> None:
    metrics = base14_metrics_for(_font("Helvetica"))
    assert metrics is not None
    width, missing = natural_text_width("Hamburg", 12.0, metrics)
    assert missing == 0
    assert 30 < width < 60  # sane Helvetica width for 7 chars at 12pt

    # Bold variant must differ from regular (different metric table).
    bold = base14_metrics_for(_font("Helvetica-Bold", weight="bold"))
    bold_width, _ = natural_text_width("Hamburg", 12.0, bold)
    assert bold_width > width


def test_base14_metrics_none_for_unknown_families() -> None:
    assert base14_metrics_for(_font("TotallyCustom")) is None
