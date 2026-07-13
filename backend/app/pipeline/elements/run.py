from dataclasses import dataclass, field

from app.core.enums import ReconstructionMode
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.glyph import Glyph


# The style attributes that define a run's identity. Two adjacent stretches
# of text belong to the SAME run — and must NOT be split into separate
# `<span>`s — when every one of these is equal. This is the merge contract
# the Run Builder (Phase 2) enforces; `Run.style_key` derives it so the
# builder and any validator agree on exactly one definition. A `<span>` is a
# style boundary, never a positioning unit (ADR-011).
RUN_STYLE_ATTRS = (
    "font_id",
    "font_size",
    "color",
    "weight",
    "italic",
    "underline",
    "strike",
    "opacity",
    "render_mode",
    "rotation",
    "writing_mode",
    "language",
)


@dataclass
class Run:
    """One contiguous style within a Line (ADR-001/011). A Run is the unit a
    `<span>` maps to — and only when its style differs from the paragraph's
    default. Adjacent glyphs collapse into a single Run whenever every
    attribute in `RUN_STYLE_ATTRS` is identical, so the "New York Times"
    span-per-word / mid-word-split explosion cannot occur by construction.

    `text` is the run's source of truth. A run owns ONLY style — words live on
    the Line (Phase 2.6), since a lexical word may span several runs. `glyphs`
    is populated only for GLYPH-mode runs (M2). `expected_width`/`actual_width`
    come from the frozen Adaptive Reconstruction decision — consumed here,
    never recomputed."""

    id: str
    bbox: BoundingBox
    text: str
    font_id: str | None = None
    font_size: float = 0.0
    color: str = "#000000"
    weight: int = 400  # 400 = normal, 700 = bold
    italic: bool = False
    underline: bool = False
    strike: bool = False
    opacity: float = 1.0
    render_mode: int = 0  # PDF Tr operator (0 = fill)
    rotation: float = 0.0
    writing_mode: str = "horizontal-tb"
    language: str | None = None
    # PDF text-state operators (LFS: document typography, not renderer data).
    # letter_spacing (Tc) is measured (Issue 002B, character_spacing.py) —
    # genuine author tracking. rise is MEASURED baseline offset (px, positive
    # = raised above the line's main baseline; Renderer Geometry Investigation
    # proved it in the field: a display line raised `the` 10.86px). word_
    # spacing (Tw) and horizontal_scale (Tz) remain RESERVED — no corpus
    # evidence yet.
    letter_spacing: float = 0.0
    word_spacing: float = 0.0  # reserved (Tw); not yet extracted
    horizontal_scale: float = 1.0  # reserved (Tz); not yet extracted
    rise: float = 0.0  # measured baseline rise (measure_span_rises)
    features: list[str] = field(default_factory=list)  # OpenType feature tags
    actual_width: float = 0.0
    expected_width: float = 0.0
    mode: str = ReconstructionMode.RUN.value
    glyphs: list[Glyph] = field(default_factory=list)

    def style_key(self) -> tuple:
        """The identity two runs must share to be mergeable (see
        RUN_STYLE_ATTRS). Font size is rounded to hundredths so
        floating-point noise from extraction never forces a spurious split."""
        return tuple(
            round(v, 2) if isinstance(v, float) else v
            for v in (getattr(self, attr) for attr in RUN_STYLE_ATTRS)
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bbox": self.bbox.to_dict(),
            "text": self.text,
            "font_id": self.font_id,
            "font_size": self.font_size,
            "color": self.color,
            "weight": self.weight,
            "italic": self.italic,
            "underline": self.underline,
            "strike": self.strike,
            "opacity": self.opacity,
            "render_mode": self.render_mode,
            "rotation": self.rotation,
            "writing_mode": self.writing_mode,
            "language": self.language,
            "letter_spacing": self.letter_spacing,
            "word_spacing": self.word_spacing,
            "horizontal_scale": self.horizontal_scale,
            "rise": self.rise,
            "features": list(self.features),
            "actual_width": self.actual_width,
            "expected_width": self.expected_width,
            "mode": self.mode,
            "glyphs": [g.to_dict() for g in self.glyphs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Run":
        # Tolerate the pre-2.6 `words` key (words moved to the Line).
        data = {k: v for k, v in data.items() if k != "words"}
        return cls(
            **{
                **data,
                "bbox": BoundingBox.from_dict(data["bbox"]),
                "features": list(data.get("features", [])),
                "glyphs": [Glyph.from_dict(g) for g in data.get("glyphs", [])],
            }
        )
