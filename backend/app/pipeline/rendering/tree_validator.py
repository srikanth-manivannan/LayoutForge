"""RenderTreeValidator (RIL Rule 6) — the gate between the Instruction
Builder and every compiler. A tree that fails here never reaches a compiler.

Content fidelity is checked as NON-WHITESPACE unicode equality — every
visible character must survive exactly (line joins were a historical
source of layout-only whitespace; the Line Layout Engine removed joins
entirely — each PDF line is its own DOM element now). Also: paragraph
coverage (nested under regions), line coverage (nested under paragraphs —
every PDF line must appear as its own line node, never merged, never
split), stable-id uniqueness, and geometry presence appropriate to each
node's mode.

**Line-as-absolute-primitive (2026-07-15b):** every line is now ABSOLUTE
and REQUIRED to carry its own `top`/`left` — the inverse of the old Rule 0,
which forbade a flowed line from asserting position because two owners (an
absolute position AND a flow role) was the exact bug that model existed to
prevent. Now a line has exactly one owner of its position: itself. Rule 0
still applies to paragraphs — a paragraph is `NORMAL` (semantic, static)
and must never assert position/height, since it no longer flows anything
that a competing absolute position could conflict with; it should simply
have none."""

from collections import Counter

from app.pipeline.elements.page import Page
from app.pipeline.rendering.render_tree import ABSOLUTE, NORMAL, RenderNode


class RenderTreeValidationError(Exception):
    """The Render Tree does not faithfully cover the Rich IDM — compiling it
    is forbidden."""


# Rule 0.1 (2026-07-13): an explicit allow/deny list on flow paragraphs, so a
# future edit cannot silently reintroduce geometry into a node the browser is
# supposed to own. Checked against BOTH `geometry` and `style` dict keys —
# either one emitting a forbidden property is a violation.
_FORBIDDEN_ON_FLOW_PARAGRAPH = {
    "position", "transform", "transform-origin",
    "top", "left", "right", "bottom", "height", "min-height", "max-height",
}
_ALLOWED_ON_FLOW_PARAGRAPH = {
    # Base-run style properties (paragraph carries the dominant run's look).
    # Rendering Stabilization phase: these are now always present (complete
    # inline style, Style Registry bypassed) rather than only-when-differing.
    # No geometry keys at all (2026-07-15b) — a paragraph flows nothing, so
    # `width`/`margin-*`/`text-align`/`text-indent` would be unowned.
    "color", "font-family", "font-size", "font-weight", "font-style",
    "letter-spacing", "word-spacing", "writing-mode",
}

# Rule 0.1 at line granularity (2026-07-15b, line-as-absolute-primitive): a
# line is ABSOLUTE and its `top`/`left` are REQUIRED (checked separately,
# below) — the allow list here covers what else it may legitimately carry:
# `line-height` (sets the local half-leading term _line_offset relies on),
# `width`/`transform`/`transform-origin` (rotated lines only — see
# render_tree.py's `_line_rotation_geometry`), and a typography override
# (normally empty — the base style lives on the paragraph; this exists for
# the same reason runs can override style).
_FORBIDDEN_ON_ABSOLUTE_LINE = {
    "margin-top", "margin-bottom", "margin-left", "margin-right",
    "right", "bottom", "min-height", "max-height", "position",
}
_ALLOWED_ON_ABSOLUTE_LINE = {
    "top", "left", "line-height", "width", "transform", "transform-origin",
    "color", "font-family", "font-size", "font-weight", "font-style",
    "letter-spacing", "word-spacing", "writing-mode",
}


def _nonspace(text: str) -> Counter:
    return Counter(ch for ch in text if not ch.isspace())


def validate_render_tree(tree: RenderNode, page: Page) -> None:
    # 1. Non-whitespace unicode coverage vs the Rich IDM (multiset equality:
    #    no character lost, none invented; join spaces are layout).
    idm_text = _nonspace("".join(
        run.text
        for region in page.regions
        for paragraph in region.paragraphs
        for line in paragraph.lines
        for run in line.runs
    ))
    tree_text = _nonspace("".join(node.text for node in tree.iter_runs()))
    if idm_text != tree_text:
        missing = idm_text - tree_text
        extra = tree_text - idm_text
        raise RenderTreeValidationError(
            f"page {page.number}: render tree unicode mismatch "
            f"(missing={dict(list(missing.items())[:5])}, extra={dict(list(extra.items())[:5])})"
        )

    # 2. Paragraph coverage: every non-empty IDM paragraph appears once,
    #    nested under its region.
    idm_paragraphs = sum(
        1 for r in page.regions for p in r.paragraphs
        if any(line.runs for line in p.lines)
    )
    got_paragraphs = sum(1 for _ in tree.iter_paragraphs())
    if got_paragraphs != idm_paragraphs:
        raise RenderTreeValidationError(
            f"page {page.number}: paragraph count diverges ({got_paragraphs}/{idm_paragraphs})"
        )

    # 2b. Line coverage (2026-07-15, Line Layout Engine): every PDF line of
    # every non-empty paragraph must appear as its own line node — never
    # merged into a neighbor, never split into more than one. This is the
    # user's validation criterion (1): HTML line count == PDF line count.
    idm_lines = sum(
        1 for r in page.regions for p in r.paragraphs
        for line in p.lines if line.runs
    )
    got_lines = sum(1 for _ in tree.iter_lines())
    if got_lines != idm_lines:
        raise RenderTreeValidationError(
            f"page {page.number}: line count diverges ({got_lines}/{idm_lines}) — "
            f"every PDF line must become exactly one line node, never merged or split"
        )

    # 3. Stable ids unique; 4. geometry appropriate to mode (Rule 0).
    seen: set = set()

    def walk(node: RenderNode) -> None:
        if node.object_id in seen:
            raise RenderTreeValidationError(f"duplicate render node id {node.object_id}")
        seen.add(node.object_id)
        if node.mode == ABSOLUTE and node.kind != "page" and not node.geometry:
            raise RenderTreeValidationError(f"{node.kind} {node.object_id} is ABSOLUTE but has no geometry")
        if node.kind == "paragraph" and node.mode == NORMAL:
            # Rule 0: a flowed paragraph's extent is browser-owned. It must
            # NEVER assert top/height — that would recreate the two-owner
            # overlap bug (position PDF-absolute, extent browser-flow).
            forbidden = {"top", "height", "left"} & node.geometry.keys()
            if forbidden:
                raise RenderTreeValidationError(
                    f"paragraph {node.object_id} is flowed (NORMAL) but asserts "
                    f"{forbidden} — Rule 0 violation (one dimension, one owner)"
                )
            # Rule 0.1: explicit allow/deny list, checked against BOTH
            # geometry and style — closes the gap Rule 0 left (Rule 0 only
            # ever checked 3 keys; a future style declaration could still
            # smuggle in `position: absolute` or a `transform: translate`).
            for source_name, source in (("geometry", node.geometry), ("style", node.style)):
                bad = _FORBIDDEN_ON_FLOW_PARAGRAPH & source.keys()
                if bad:
                    raise RenderTreeValidationError(
                        f"paragraph {node.object_id} is flowed (NORMAL) but its {source_name} "
                        f"asserts forbidden propert{'y' if len(bad) == 1 else 'ies'} {bad} — "
                        f"Rule 0.1 violation"
                    )
                unlisted = source.keys() - _ALLOWED_ON_FLOW_PARAGRAPH - _FORBIDDEN_ON_FLOW_PARAGRAPH
                if unlisted:
                    raise RenderTreeValidationError(
                        f"paragraph {node.object_id} is flowed (NORMAL) but its {source_name} "
                        f"declares {unlisted}, not on the Rule 0.1 allow list — "
                        f"either it's a mistake or the allow list needs updating"
                    )
        if node.kind == "line" and node.mode == ABSOLUTE:
            # Line-as-absolute-primitive (2026-07-15b): a line's position is
            # its own — `top`/`left` are REQUIRED, not forbidden. Missing
            # either is the replacement safety rail for the old Rule 0: an
            # absolute node with no position is exactly as broken as a
            # flowed node asserting one.
            missing = {"top", "left"} - node.geometry.keys()
            if missing:
                raise RenderTreeValidationError(
                    f"line {node.object_id} is ABSOLUTE but is missing {missing} — "
                    f"an absolutely positioned line must own its position"
                )
            for source_name, source in (("geometry", node.geometry), ("style", node.style)):
                bad = _FORBIDDEN_ON_ABSOLUTE_LINE & source.keys()
                if bad:
                    raise RenderTreeValidationError(
                        f"line {node.object_id} is ABSOLUTE but its {source_name} "
                        f"asserts forbidden propert{'y' if len(bad) == 1 else 'ies'} {bad} — "
                        f"Rule 0.1 violation"
                    )
                unlisted = source.keys() - _ALLOWED_ON_ABSOLUTE_LINE - _FORBIDDEN_ON_ABSOLUTE_LINE
                if unlisted:
                    raise RenderTreeValidationError(
                        f"line {node.object_id} is ABSOLUTE but its {source_name} "
                        f"declares {unlisted}, not on the Rule 0.1 allow list — "
                        f"either it's a mistake or the allow list needs updating"
                    )
        for child in node.children:
            walk(child)

    walk(tree)
