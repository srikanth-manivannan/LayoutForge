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

Output shape — semantic HTML, production-editable, line-as-absolute-
primitive (2026-07-15b):

    <div class="lf-region" style="left/top/width (PDF-owned, one anchor)">
      <p class="lf-paragraph" style="color: ...; font-family: ...; ...">
        <span class="lf-line" style="left: ...px; top: ...px; line-height: ...px">
          plain text<span style="font-family: ...; font-weight: bold; ...">only where style changes</span>
        </span><span class="lf-line" style="left: ...px; top: ...px; line-height: ...px">…</span>
      </p>
      <p class="lf-paragraph" style="...">…</p>
    </div>

Paragraphs are `position:static` (asserted via `.lf-paragraph` in CSS, not
here) — a purely SEMANTIC container that never flows or positions text.
Every PDF line is its own `<span class="lf-line">`, absolutely positioned
directly from its own `baseline_y`/`bbox.x` (region-relative — see
render_tree.py's `_build_line_nodes`/`_line_offset`), never from CSS flow,
never from a predicted sibling or paragraph size. A `<span>` inside a line
is a style-change optimization for a Run, never a word.
"""

from markupsafe import escape

from app.pipeline.rendering.render_tree import RenderNode


def _inline(declarations: dict) -> str:
    return "; ".join(f"{k}: {v}" for k, v in declarations.items())


def run_declarations(node: RenderNode) -> dict:
    """A run child's full CSS declarations (style + measured rise)."""
    declarations = dict(node.style)
    if node.rise:
        declarations["position"] = "relative"
        declarations["top"] = f"{-node.rise:g}px"
    return declarations


def _compile_line(line: RenderNode) -> str:
    inner: list[str] = []
    for run in line.children:
        text = str(escape(run.text))
        declarations = run_declarations(run)
        if not declarations:
            inner.append(text)  # base style → plain text node
            continue
        inner.append(f'<span style="{escape(_inline(declarations))}">{text}</span>')
    attrs = f' style="{escape(_inline(line.geometry))}"' if line.geometry else ""
    return f'<span class="lf-line" data-object-id="{line.object_id}"{attrs}>{"".join(inner)}</span>'


def _compile_paragraph(paragraph: RenderNode) -> str:
    inner = "".join(_compile_line(line) for line in paragraph.children)
    tag = "p"
    # A paragraph is always position:static (2026-07-15b) — it carries no
    # geometry of its own; every line positions itself absolutely.
    full_style = {**paragraph.geometry, **paragraph.style}
    return (
        f'<{tag} class="lf-paragraph" data-type="text" data-object-id="{paragraph.object_id}" '
        f'style="{escape(_inline(full_style))}">{inner}</{tag}>'
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
