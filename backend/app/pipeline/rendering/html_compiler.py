"""HTML compiler (RIL) — a PURE compiler over the Render Tree.

Binding import rule (enforced by test_ril_compiler_purity): this module may
import ONLY the Render Tree — never Paragraph/Line/Run/Word/Glyph. It never
measures, never decides — every value it emits was computed by the
Instruction Builder.

**Rendering Stabilization phase (temporary, 2026-07-13):** the Style
Registry is bypassed — every rendered element carries its own COMPLETE
inline style, no `lf-p*`/`lf-r*`/`lf-s*` dedup classes, so a single class
change can never silently move unrelated elements while the renderer is
still being debugged. Structural classes (`lf-region`, `lf-paragraph`) stay
— they carry layout MECHANICS (position, margin reset, white-space), never
typography. Future work (only after Golden Corpus + visual validation pass):
reintroduce the Style Registry as a separate dedup PASS over these inline
styles (Inline Styles -> Style Analyzer -> Style Deduplicator -> CSS
Classes) — the renderer itself must stay deterministic and independent of
that optimization.

Output shape — semantic HTML, production-editable, Rule-0 compliant:

    <div class="lf-region" style="left/top/width (PDF-owned, one anchor)">
      <p class="lf-paragraph" style="width; margin-top: <PDF gap>; color: ...; font-family: ...; ...">
        plain text<span style="font-family: ...; font-weight: bold; ...">only where style changes</span>
      </p>
      <p class="lf-paragraph" style="...">…</p>
    </div>

Paragraphs are normal-flow block elements (NOT position:absolute) — the
browser stacks them, using the margin-top the Instruction Builder computed
from the PDF's own inter-paragraph gap. There is no line element and no
per-paragraph height. A span is an HTML optimization for a style change,
never a Run, never a word.
"""

from markupsafe import escape

from app.pipeline.rendering.render_tree import ABSOLUTE, RenderNode


def _inline(declarations: dict) -> str:
    return "; ".join(f"{k}: {v}" for k, v in declarations.items())


def run_declarations(node: RenderNode) -> dict:
    """A run child's full CSS declarations (style + measured rise)."""
    declarations = dict(node.style)
    if node.rise:
        declarations["position"] = "relative"
        declarations["top"] = f"{-node.rise:g}px"
    return declarations


def _compile_paragraph(paragraph: RenderNode) -> str:
    inner: list[str] = []
    for run in paragraph.children:
        text = str(escape(run.text))
        declarations = run_declarations(run)
        if not declarations:
            inner.append(text)  # base style → plain text node
            continue
        inner.append(f'<span style="{escape(_inline(declarations))}">{text}</span>')
    tag = "p"
    position = "position: absolute; " if paragraph.mode == ABSOLUTE else ""
    full_style = {**paragraph.geometry, **paragraph.style}
    return (
        f'<{tag} class="lf-paragraph" data-type="text" data-object-id="{paragraph.object_id}" '
        f'style="{escape(position + _inline(full_style))}">{"".join(inner)}</{tag}>'
    )


def compile_page_text_layer(tree: RenderNode) -> list[str]:
    """One `<div class="lf-region">` fragment per region, each containing its
    paragraphs in reading/flow order."""
    fragments: list[str] = []
    for region in tree.children:
        if region.kind != "region":
            continue
        paragraphs_html = "".join(_compile_paragraph(p) for p in region.children)
        fragments.append(
            f'<div class="lf-region" data-object-id="{region.object_id}" '
            f'style="{escape(_inline(region.geometry))}">{paragraphs_html}</div>'
        )
    return fragments
