"""Style Registry (Phase 3): identical styles collapse to one class; distinct
styles get distinct classes; empty declarations produce no class."""

from app.pipeline.outputs.writers.style_registry import StyleRegistry


def test_identical_styles_share_one_class() -> None:
    reg = StyleRegistry()
    a = reg.run_class({"color": "#000", "font-size": "12px"})
    b = reg.run_class({"font-size": "12px", "color": "#000"})  # order-independent
    assert a == b
    assert len(reg) == 1


def test_distinct_styles_get_distinct_classes() -> None:
    reg = StyleRegistry()
    a = reg.run_class({"color": "#000"})
    b = reg.run_class({"color": "#f00"})
    assert a != b
    assert reg.css().count("{") == 2


def test_empty_declarations_yield_no_class() -> None:
    reg = StyleRegistry()
    assert reg.paragraph_class({}) == ""
    assert reg.paragraph_class({"text-align": ""}) == ""
    assert len(reg) == 0
