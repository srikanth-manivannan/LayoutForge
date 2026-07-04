"""Font Metrics — measure text width from real font advances, never
estimate (docs/design/typography/02_FONT_METRICS_ENGINE.md). Tier 1:
embedded font files via fontTools. Tier 2: PDF base-14 standard fonts via
MuPDF's built-in metric tables. Used by the Adaptive Reconstruction Engine.

Kept in its own module (extracted from normalize_idm) so the reconstruction
engine and future glyph engine (M2) share one metrics source; re-exported
from normalize_idm for backward-compatible imports."""

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import fitz
from fontTools.ttLib import TTFont

from app.pipeline.elements.font import FontResource

logger = logging.getLogger("layoutforge.pipeline")

# A word whose measured coverage is below this is treated as unmeasurable
# (too many glyphs missing from the subset) — we never fit on a bad measure.
MAX_MISSING_CHAR_FRACTION = 0.2


@dataclass
class FontMetrics:
    """Just enough of an extracted font FILE to measure text:
    char → glyph → advance."""

    cmap: dict[int, str]
    advances: dict[str, tuple[int, int]]
    units_per_em: int

    def advance(self, char: str) -> float | None:
        glyph = self.cmap.get(ord(char))
        if glyph is None or glyph not in self.advances:
            return None
        return float(self.advances[glyph][0])


class Base14Metrics:
    """Metrics for the PDF standard fonts (Times/Helvetica/Courier…), which
    are referenced but never embedded. MuPDF ships their exact metric tables
    — the same metrics Times New Roman/Arial/Courier New carry locally,
    which is what css_family_stack maps these fonts to — so measuring with
    them keeps overlay width fitting exact for non-embedded standard fonts."""

    units_per_em = 1000

    def __init__(self, font: fitz.Font) -> None:
        self._font = font

    def advance(self, char: str) -> float | None:
        codepoint = ord(char)
        if not self._font.has_glyph(codepoint):
            return None
        return self._font.glyph_advance(codepoint) * self.units_per_em


_BASE14_BY_TOKEN = {
    "times": ("tiro", "tibo", "tiit", "tibi"),
    "helvetica": ("helv", "hebo", "heit", "hebi"),
    "arial": ("helv", "hebo", "heit", "hebi"),
    "courier": ("cour", "cobo", "coit", "cobi"),
}


def base14_metrics_for(font: FontResource) -> Base14Metrics | None:
    lowered = font.family.lower()
    for token, (regular, bold, italic, bold_italic) in _BASE14_BY_TOKEN.items():
        if token not in lowered:
            continue
        is_bold = font.weight in ("bold", "semibold", "extrabold", "black")
        is_italic = font.style == "italic"
        name = bold_italic if (is_bold and is_italic) else bold if is_bold else italic if is_italic else regular
        try:
            return Base14Metrics(fitz.Font(name))
        except Exception:  # noqa: BLE001 - metrics are best-effort
            return None
    return None


def load_font_metrics(font_path: Path) -> FontMetrics | None:
    try:
        font = TTFont(io.BytesIO(font_path.read_bytes()))
        return FontMetrics(
            cmap=font.getBestCmap() or {},
            advances=dict(font["hmtx"].metrics),
            units_per_em=font["head"].unitsPerEm or 1000,
        )
    except Exception:  # noqa: BLE001 - unmeasurable font simply disables fitting for its blocks
        logger.warning("width-fit: could not load metrics from %s", font_path.name, exc_info=True)
        return None


def natural_text_width(text: str, font_size: float, metrics: "FontMetrics | Base14Metrics") -> tuple[float, int]:
    """Width the browser will lay this text out at (no kerning — CSS default
    for these generated pages), plus how many characters had no glyph in the
    font (measured with a .notdef-like ½-em guess)."""
    total_units = 0.0
    missing = 0
    for char in text:
        units = metrics.advance(char)
        if units is not None:
            total_units += units
        else:
            missing += 1
            total_units += metrics.units_per_em / 2
    return total_units / metrics.units_per_em * font_size, missing


FontMetricsByFont = "dict[str, FontMetrics | Base14Metrics | None]"
