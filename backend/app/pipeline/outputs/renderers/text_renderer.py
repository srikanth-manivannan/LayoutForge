from jinja2 import Template
from markupsafe import escape

from app.pipeline.elements.font import FontResource
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.outputs.font_naming import css_family_stack


class TextRenderer:
    """Renders a normalized TextBlock (one PDF line) into an accessible
    <p> container.

    Two paths, chosen per block:
    - WORD-PINNED (typography Milestone 1, when `block.words` is present):
      each word is an absolutely-positioned <span> at its true x offset
      within the line. Cross-word gaps are the PDF's own — no line-level
      spacing crutch, so no drift/ghosting can accumulate across the line.
    - SPAN (fallback, rotated/RTL/unresolved lines): one inline <span> per
      style run, with block-level letter/word-spacing from width fitting.

    Either way the <p> keeps its object identity (data-object-id) and the
    line's geometry; span font-family uses the unique-per-resource naming
    (font_naming.py) so every run loads exactly its own font file."""

    def __init__(self, template: Template, fonts_by_id: dict[str, FontResource] | None = None) -> None:
        self._template = template
        self._fonts_by_id: dict[str, FontResource] = fonts_by_id or {}

    def _resolve_family(self, font_id: str | None) -> str:
        if not font_id:
            return ""
        font = self._fonts_by_id.get(font_id)
        return font.family if font else font_id  # fall back to UUID only if unresolvable

    def _span_style(self, span: TextSpan, block: TextBlock) -> str:
        parts = [f"color: {span.color}"]
        font = self._fonts_by_id.get(span.font_id) if span.font_id else None
        parts.append(f"font-family: {css_family_stack(font)}" if font else "font-family: inherit")
        if span.font_size and abs(span.font_size - block.font_size) > 0.01:
            parts.append(f"font-size: {span.font_size:g}px")
        return "; ".join(parts)

    def _inner(self, block: TextBlock) -> str:
        if block.words:
            parts: list[str] = []
            for word in block.words:
                font = self._fonts_by_id.get(word.font_id) if word.font_id else None
                left = word.x - block.bbox.x
                style = [
                    f"left: {left:g}px",
                    f"color: {word.color}",
                    f"font-family: {css_family_stack(font)}" if font else "font-family: inherit",
                ]
                if word.font_size and abs(word.font_size - block.font_size) > 0.01:
                    style.append(f"font-size: {word.font_size:g}px")
                if word.letter_spacing:
                    style.append(f"letter-spacing: {word.letter_spacing:g}px")
                # data-mode/data-reason expose the adaptive-reconstruction
                # decision so proofing, validation, and the future editor can
                # see which words are exact vs approximated and why.
                reason_attr = f' data-reason="{word.reason}"' if word.reason != "none" else ""
                parts.append(
                    f'<span class="lf-word" data-mode="{word.mode}"{reason_attr} '
                    f'style="{"; ".join(style)}">{escape(word.text)}</span>'
                )
            return "".join(parts)

        spans = block.spans or [
            TextSpan(text=block.text, font_id=block.font_id, font_size=block.font_size, color=block.color)
        ]
        return "".join(
            f'<span style="{self._span_style(span, block)}">{escape(span.text)}</span>' for span in spans
        )

    def render(self, block: TextBlock) -> str:
        return self._template.render(
            id=f"tb-{block.id}",
            object_id=block.id,
            page=block.page,
            font_name=self._resolve_family(block.font_id),
            rotation=block.rotation,
            reading_order=block.reading_order,
            alignment=block.alignment,
            writing_direction=block.writing_direction,
            word_pinned="true" if block.words else "false",
            inner=self._inner(block),
        )
