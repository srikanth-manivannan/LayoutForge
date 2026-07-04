"""The single source of the CSS font-family naming scheme, shared by the
CSS generator (@font-face + block rules) and the HTML text renderer (span
inline styles) so they can never drift apart.

Why unique-per-resource families: a PDF routinely embeds several SUBSETS of
the same typeface (e.g. two "ComicSansMS" subsets — often one regular, one
bold, each carrying only its own glyphs). If both declared the same CSS
family, the browser would pick one file for every run of that family —
wrong glyphs (missing from that subset) and wrong weight for the other.
Giving every FontResource its own family name guarantees each text run
loads exactly the font file it was extracted with — the pixel-accuracy
contract. The original family stays in the stack as a best-effort local
fallback for fonts that couldn't be embedded at all."""

from app.pipeline.elements.font import FontResource


def css_family_name(font: FontResource) -> str:
    """Unique, human-readable CSS family for one extracted font resource."""
    return f"{font.family} lf{font.id[:8]}"


# Metric-compatible local stacks for the PDF standard fonts ("base-14"),
# which are referenced but never embedded — Times New Roman/Arial/Courier
# New carry the same metrics as the PostScript originals, so mapping to
# them keeps overlay text the same width as the raster. First matching
# token wins (ordered so "courier" can't be shadowed by broader tokens).
_LOCAL_METRIC_STACKS: list[tuple[str, str]] = [
    ("courier", '"Courier New", Courier, monospace'),
    ("times", '"Times New Roman", Times, serif'),
    ("helvetica", "Arial, Helvetica, sans-serif"),
    ("arial", "Arial, Helvetica, sans-serif"),
    ("symbol", "Symbol, serif"),
    ("zapf", '"Zapf Dingbats", serif'),
]


def css_family_stack(font: FontResource | None) -> str:
    if font is None:
        return "sans-serif"
    if not font.filename:
        # No file to serve: map the standard fonts onto their
        # metric-compatible local equivalents instead of generic sans.
        lowered = font.family.lower()
        for token, stack in _LOCAL_METRIC_STACKS:
            if token in lowered:
                return f'"{font.family}", {stack}'
        return f'"{font.family}", sans-serif'
    return f'"{css_family_name(font)}", "{font.family}", sans-serif'


# CSS font-weight values per token; "normal"/"bold" stay keywords (existing
# manifests/tests), richer tokens map to their numeric weights.
CSS_WEIGHT_BY_TOKEN = {
    "thin": "100",
    "extralight": "200",
    "light": "300",
    "normal": "normal",
    "medium": "500",
    "semibold": "600",
    "bold": "bold",
    "extrabold": "800",
    "black": "900",
}


def css_weight(font: FontResource) -> str:
    return CSS_WEIGHT_BY_TOKEN.get(font.weight, "normal")
