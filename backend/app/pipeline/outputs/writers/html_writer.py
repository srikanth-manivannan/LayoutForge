"""Semantic HTML writer (ADR-011, Phase 3).

Compiles the Rich IDM to reflowable, semantic HTML — the opposite of the
legacy word-pinned output that emitted a `<span>` per word. The hierarchy is
preserved end to end:

    Document → Page → Region(<div>) → Paragraph(<p>) → Line(<span.lf-line>)
             → Run(text, or <span> only on a real style change) → Text

Ownership is strict (LFS §5): the paragraph class carries layout metrics
(line-height, align, indent, margins, direction) *and* the paragraph's base
run style, so a run that matches the base emits **plain text** and only a
genuine style change becomes a `<span>`. Adjacent base runs coalesce into one
text node. Styles are deduplicated through the Style Registry. Every page is
checked for character fidelity before it is returned.
"""

from html import escape
from html.parser import HTMLParser
from unicodedata import normalize

from app.pipeline.elements.line import Line
from app.pipeline.elements.paragraph import Paragraph
from app.pipeline.elements.region import Region
from app.pipeline.elements.run import Run
from app.pipeline.outputs.font_naming import css_family_stack
from app.pipeline.outputs.writers.base import Writer, WriterResult
from app.pipeline.outputs.writers.context import Target, WriterContext
from app.pipeline.outputs.writers.style_registry import StyleRegistry

_ROLE_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li"}


class HtmlFidelityError(Exception):
    """Raised when generated HTML would lose or alter a character vs the tree."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def _nonspace(text: str) -> str:
    return "".join(normalize("NFC", text).split())


class HtmlWriter(Writer):
    target = Target.HTML

    def write(self, ctx: WriterContext) -> WriterResult:
        registry = StyleRegistry()
        # Pass 1: render bodies (populates the registry). Pass 2: wrap with the
        # now-complete, deduplicated stylesheet so every page shares it.
        bodies: list[tuple[int, str]] = []
        for page in ctx.document.pages:
            body = "".join(self._render_region(region, registry, ctx) for region in page.regions)
            self._assert_fidelity(page, body)
            bodies.append((page.number, body))

        css = registry.css()
        pages = [(number, self._document(number, body, css)) for number, body in bodies]
        return WriterResult(pages=pages, stylesheet=css)

    # ---- geometry-free semantic rendering ------------------------------

    def _render_region(self, region: Region, registry: StyleRegistry, ctx: WriterContext) -> str:
        inner = "".join(self._render_paragraph(p, registry, ctx) for p in region.paragraphs)
        attrs = ' class="lf-region"'
        if ctx.flags.emit_stable_ids:
            attrs += f' data-object-id="{region.id}"'
        attrs += f' data-kind="{region.kind}"'
        return f"<div{attrs}>{inner}</div>"

    def _render_paragraph(self, paragraph: Paragraph, registry: StyleRegistry, ctx: WriterContext) -> str:
        runs = [run for line in paragraph.lines for run in line.runs]
        base_key = self._base_key(runs, ctx)
        base_run = next((r for r in runs if self._run_key(r, ctx) == base_key), None)

        decl = self._paragraph_declarations(paragraph, base_run, ctx)
        pclass = registry.paragraph_class(decl)
        classes = "lf-paragraph" + (f" {pclass}" if pclass else "")

        tag = paragraph.role if paragraph.role in _ROLE_TAGS else "p"
        attrs = f' class="{classes}"'
        if ctx.flags.emit_stable_ids:
            attrs += f' data-object-id="{paragraph.id}"'
        if ctx.flags.emit_debug_attributes:
            attrs += f' data-confidence="{paragraph.confidence:g}"'
            if paragraph.signals:
                attrs += f' data-signals="{",".join(paragraph.signals)}"'

        # Lines are separated by a space so reflow keeps word boundaries; that
        # space is whitespace and never a fidelity-tracked character.
        inner = " ".join(self._render_line(line, base_key, registry, ctx) for line in paragraph.lines)
        return f"<{tag}{attrs}>{inner}</{tag}>"

    def _render_line(self, line: Line, base_key: tuple, registry: StyleRegistry, ctx: WriterContext) -> str:
        parts: list[str] = []
        buffer: list[str] = []  # coalesce consecutive base-style runs into one text node
        for run in line.runs:
            # A whitespace-only run has no visible glyph, so its style is
            # irrelevant — it must never force a style boundary/span. Fold it
            # into the surrounding text like any base-style run.
            if not run.text.strip() or self._run_key(run, ctx) == base_key:
                buffer.append(run.text)
                continue
            if buffer:
                parts.append(escape("".join(buffer)))
                buffer = []
            rclass = registry.run_class(self._run_declarations(run, ctx))
            rattrs = f' class="{rclass}"' if rclass else ""
            if ctx.flags.emit_stable_ids:
                rattrs += f' data-object-id="{run.id}"'
            parts.append(f"<span{rattrs}>{escape(run.text)}</span>")
        if buffer:
            parts.append(escape("".join(buffer)))

        lattrs = ' class="lf-line"'
        if ctx.flags.emit_stable_ids:
            lattrs += f' data-object-id="{line.id}"'
        return f"<span{lattrs}>{''.join(parts)}</span>"

    # ---- style ownership -----------------------------------------------

    def _run_declarations(self, run: Run, ctx: WriterContext) -> dict[str, str]:
        """Runs own ONLY visual style: font, size, weight, italic, color,
        decoration (LFS §5). No layout, geometry, or spacing here."""
        font = ctx.fonts_by_id.get(run.font_id or "")
        decl: dict[str, str] = {
            "font-family": css_family_stack(font),
            "font-size": f"{run.font_size:g}px",
            "color": run.color,
        }
        if run.weight and run.weight >= 700:
            decl["font-weight"] = "700"
        if run.italic:
            decl["font-style"] = "italic"
        decorations = []
        if run.underline:
            decorations.append("underline")
        if run.strike:
            decorations.append("line-through")
        if decorations:
            decl["text-decoration"] = " ".join(decorations)
        return decl

    def _paragraph_declarations(
        self, paragraph: Paragraph, base_run: Run | None, ctx: WriterContext
    ) -> dict[str, str]:
        """Paragraphs own layout metrics; the base run style is folded in so
        matching runs inherit it and need no span."""
        decl: dict[str, str] = {}
        if ctx.flags.emit_paragraph_metrics:
            if paragraph.alignment and paragraph.alignment != "left":
                decl["text-align"] = paragraph.alignment
            if paragraph.line_height:
                decl["line-height"] = f"{paragraph.line_height:g}px"
            if paragraph.first_line_indent:
                decl["text-indent"] = f"{paragraph.first_line_indent:g}px"
            if paragraph.space_before:
                decl["margin-top"] = f"{paragraph.space_before:g}px"
            if paragraph.space_after:
                decl["margin-bottom"] = f"{paragraph.space_after:g}px"
            if paragraph.writing_direction == "rtl":
                decl["direction"] = "rtl"
        if base_run is not None:
            decl.update(self._run_declarations(base_run, ctx))
        return decl

    def _run_key(self, run: Run, ctx: WriterContext) -> tuple:
        return tuple(sorted(self._run_declarations(run, ctx).items()))

    def _base_key(self, runs: list[Run], ctx: WriterContext) -> tuple:
        """The paragraph's dominant run style — the one covering the most text,
        so the fewest runs need an overriding span."""
        weights: dict[tuple, int] = {}
        for run in runs:
            weights[self._run_key(run, ctx)] = weights.get(self._run_key(run, ctx), 0) + len(run.text)
        return max(weights, key=weights.get) if weights else ()

    # ---- fidelity + document wrapper -----------------------------------

    def _assert_fidelity(self, page, body: str) -> None:
        tree_text = _nonspace(
            "".join(
                run.text
                for region in page.regions
                for paragraph in region.paragraphs
                for line in paragraph.lines
                for run in line.runs
            )
        )
        extractor = _TextExtractor()
        extractor.feed(body)
        html_text = _nonspace("".join(extractor.text))
        if tree_text != html_text:
            raise HtmlFidelityError(
                f"HTML fidelity mismatch on page {page.number}: "
                f"tree={len(tree_text)} chars vs html={len(html_text)} chars"
            )

    def _document(self, page_number: int, body: str, css: str) -> str:
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f"<title>Page {page_number}</title>\n"
            f"<style>\n{css}\n</style>\n</head>\n"
            f'<body>\n<main class="lf-document">\n{body}\n</main>\n</body>\n</html>\n'
        )
