"""RenderTreeValidator (RIL Rule 6) — the gate between the Instruction
Builder and every compiler. A tree that fails here never reaches a compiler.

Content fidelity is checked as NON-WHITESPACE unicode equality — line joins
insert a single space (layout, not content); every visible character must
survive exactly. Also: paragraph coverage (now nested under regions),
stable-id uniqueness, and geometry presence appropriate to each node's mode
(ABSOLUTE nodes need position; flowed paragraphs need only width — Rule 0:
a flowed paragraph must NOT carry top/height, which would reassert the two-
owner bug this layer exists to prevent)."""

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
    "width", "margin-top", "margin-bottom", "margin-left", "margin-right",
    "text-align", "line-height", "text-indent", "padding",
    # Base-run style properties (paragraph carries the dominant run's look).
    # Rendering Stabilization phase: these are now always present (complete
    # inline style, Style Registry bypassed) rather than only-when-differing.
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
        for child in node.children:
            walk(child)

    walk(tree)
