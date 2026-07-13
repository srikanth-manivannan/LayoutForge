"""Font *visual* identity (ADR-011, Phase 2 Run Builder).

A Run is a contiguous sequence of glyphs that **renders identically** — not
one that shares a PDF font object. PDF font names are unreliable: the same
typeface appears as `ABCDEF+Arial`, `XYZQWE+Arial`, `ArialMT`,
`Arial-Regular`, `ArialPSMT`, `ArialSubset01`… all visually identical. The
Run Builder MUST merge across those, and MUST NOT merge across a genuine
style change (bold, italic, different family), even mid-word.

So run identity is derived from what the reader *sees* — normalized family +
weight + italic — with subset prefixes, subset serials, and foundry noise
tokens stripped. The PDF font name / subset name / object id are deliberately
absent from the key.
"""

import re

from app.pipeline.elements.font import FontResource

# `ABCDEF+` subset prefix PDF prepends to embedded subsets.
_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")

# Tokens that describe weight/slant (handled by the weight/italic axes, not
# the family) or are pure foundry noise. Stripped from the base family so
# `ChauncyPro-Regular`, `ChauncyPro`, and `ChauncyProPSMT` collapse to one
# family while `ChauncyPro-Italic` keeps a different *italic* axis.
_WEIGHT_TOKENS = {
    "thin", "hairline", "extralight", "ultralight", "light", "book", "regular",
    "roman", "normal", "medium", "semibold", "demibold", "demi", "bold",
    "extrabold", "ultrabold", "heavy", "black", "extrablack",
}
_SLANT_TOKENS = {"italic", "oblique", "slanted", "it"}
_NOISE_TOKENS = {"mt", "ps", "psmt", "pro", "std", "opentype", "truetype"}
# NOTE: "pro"/"std" are foundry variant markers (e.g. MinionPro/MinionStd are
# the SAME visual design at our altitude); dropping them is intentional. If a
# corpus proves two genuinely different faces differ only by pro/std, revisit.

_BOLD_TOKENS = {"bold", "extrabold", "ultrabold", "heavy", "black", "extrablack", "semibold", "demibold"}


def _tokenize(name: str) -> list[str]:
    no_prefix = _SUBSET_PREFIX.sub("", name)
    # split camelCase and delimiter boundaries: "ChauncyProItalic" → chauncy pro italic
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", no_prefix)
    return [t for t in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if t]


def base_family(name: str) -> str:
    """The visual family, stripped of subset prefix/serials and weight/slant/
    noise tokens. `ABCDEF+Arial-BoldMT` → `arial`; `ChauncyPro-Italic` →
    `chauncy` (the pro/italic axes live elsewhere)."""
    core = [
        t
        for t in _tokenize(name)
        if t not in _WEIGHT_TOKENS
        and t not in _SLANT_TOKENS
        and t not in _NOISE_TOKENS
        and not re.fullmatch(r"subset\d*", t)
        and not t.isdigit()
    ]
    return "".join(core) or _SUBSET_PREFIX.sub("", name).lower()


def is_bold(font: FontResource) -> bool:
    if font.weight and font.weight.lower() in _BOLD_TOKENS:
        return True
    return any(t in _BOLD_TOKENS for t in _tokenize(font.original_name or font.family))


def is_italic(font: FontResource) -> bool:
    if font.style and font.style.lower() in _SLANT_TOKENS:
        return True
    return any(t in _SLANT_TOKENS for t in _tokenize(font.original_name or font.family))


def visual_style_key(font: FontResource | None) -> tuple:
    """The identity two fonts must share to render identically: normalized
    family, bold, italic. Subset name / object id are intentionally excluded —
    that is the whole point (ADR-011). `None` → a distinct 'unknown' identity
    so unresolved fonts never silently merge with resolved ones."""
    if font is None:
        return ("", False, False, "__unresolved__")
    return (base_family(font.original_name or font.family), is_bold(font), is_italic(font), "")
