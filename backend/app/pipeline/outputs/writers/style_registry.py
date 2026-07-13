"""Style Registry (ADR-011, Phase 3).

Deduplicates CSS. A document has thousands of paragraphs and runs but only a
handful of distinct *styles*; the registry maps each distinct style to one
reusable class (`lf-p3`, `lf-r7`) and emits each rule once. Inline styles
would repeat the same declarations tens of thousands of times.

The registry is format-agnostic — it holds ordered CSS declarations keyed by
their content, so the same style always yields the same class within a run.
"""


class StyleRegistry:
    def __init__(self) -> None:
        self._paragraph: dict[tuple, str] = {}
        self._run: dict[tuple, str] = {}

    def _register(self, table: dict[tuple, str], prefix: str, declarations: dict[str, str]) -> str:
        # Drop empty values so "no override" never creates a distinct style.
        items = tuple(sorted((k, v) for k, v in declarations.items() if v not in (None, "")))
        if not items:
            return ""
        cls = table.get(items)
        if cls is None:
            cls = f"{prefix}{len(table)}"
            table[items] = cls
        return cls

    def paragraph_class(self, declarations: dict[str, str]) -> str:
        return self._register(self._paragraph, "lf-p", declarations)

    def run_class(self, declarations: dict[str, str]) -> str:
        return self._register(self._run, "lf-r", declarations)

    def css(self) -> str:
        lines: list[str] = []
        for table in (self._paragraph, self._run):
            for items, cls in table.items():
                body = " ".join(f"{k}: {v};" for k, v in items)
                lines.append(f".{cls} {{ {body} }}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._paragraph) + len(self._run)
