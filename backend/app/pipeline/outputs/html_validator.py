from html.parser import HTMLParser
from pathlib import Path


class HtmlValidationError(Exception):
    """Raised when generated HTML fails validation — callers must treat
    this as fail-fast: do not write the offending file."""


class _ReferenceCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        element_id = attr_dict.get("id")
        if element_id:
            self.ids.append(element_id)
        for key in ("src", "href"):
            value = attr_dict.get(key)
            if value:
                self.references.append(value)


class HtmlValidator:
    """Validates one generated page's HTML before it's written to disk:
    no duplicate element ids, and every relative src/href must resolve to
    a real file. This is deliberately lightweight (stdlib HTMLParser, no
    full HTML5-conformance check) — it exists to catch our own template
    bugs and broken asset references, not to validate arbitrary HTML."""

    def validate(self, html: str, html_file_dir: Path) -> None:
        collector = _ReferenceCollector()
        collector.feed(html)

        errors: list[str] = []

        seen: set[str] = set()
        duplicates: set[str] = set()
        for element_id in collector.ids:
            if element_id in seen:
                duplicates.add(element_id)
            seen.add(element_id)
        if duplicates:
            errors.append(f"Duplicate element ids: {sorted(duplicates)}")

        for reference in collector.references:
            if reference.startswith(("http://", "https://", "data:", "#", "/")):
                # Absolute paths (/static/...) are server-resolved; the
                # validator has no access to the backend's URL space so
                # it can't check them via the filesystem. Relative paths
                # (../resources/...) should no longer appear now that
                # all generated URLs are absolute — their presence would
                # itself be the bug to catch.
                continue
            resolved = (html_file_dir / reference).resolve()
            if not resolved.exists():
                errors.append(f"Missing referenced file: {reference}")

        if errors:
            raise HtmlValidationError("; ".join(errors))
