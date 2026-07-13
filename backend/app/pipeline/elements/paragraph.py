from dataclasses import dataclass, field

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.line import Line


@dataclass
class Paragraph:
    """A paragraph within a Region (ADR-001/011) — the node that OWNS
    typography metrics. `line_height`, `letter_spacing`, `word_spacing`,
    `alignment`, `writing_direction`, and indents live here, not on words or
    lines; a child Run overrides one only when it genuinely differs. This is
    what lets the renderer emit `<p>` with paragraph-level CSS and reserve
    `<span>` for real style changes.

    `role` gives the semantic tag the writer emits (`p`, `h1`..`h6`,
    `blockquote`, `li`, …); it defaults to `p` until heading/list
    classification (M3 WP2) runs. A paragraph ends only on a structural
    signal — indent/alignment/direction change, baseline gap over threshold,
    explicit marker, text-frame or column change — never because a PDF
    drawing operator changed."""

    id: str
    bbox: BoundingBox
    role: str = "p"
    alignment: str = "left"  # "left" | "center" | "right" | "justify"
    writing_direction: str = "ltr"  # "ltr" | "rtl"
    first_line_indent: float = 0.0
    space_before: float = 0.0
    space_after: float = 0.0
    line_height: float = 0.0
    leading: float = 0.0
    letter_spacing: float = 0.0
    word_spacing: float = 0.0
    style_ref: str | None = None  # named paragraph style, when detected
    # Explainability (mirrors the Adaptive Reconstruction Engine, ADR-002):
    # how confident the grouping is, and which layout signals supported it.
    # Semantics come only from layout evidence, never from drawing operators
    # (LFS §2). `confidence` in [0,1]; `signals` are the contributing signal
    # names; `reason` is a short label for the decisive factor.
    confidence: float = 1.0
    reason: str = ""
    signals: list[str] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bbox": self.bbox.to_dict(),
            "role": self.role,
            "alignment": self.alignment,
            "writing_direction": self.writing_direction,
            "first_line_indent": self.first_line_indent,
            "space_before": self.space_before,
            "space_after": self.space_after,
            "line_height": self.line_height,
            "leading": self.leading,
            "letter_spacing": self.letter_spacing,
            "word_spacing": self.word_spacing,
            "style_ref": self.style_ref,
            "confidence": self.confidence,
            "reason": self.reason,
            "signals": list(self.signals),
            "lines": [line.to_dict() for line in self.lines],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Paragraph":
        return cls(
            **{
                **data,
                "bbox": BoundingBox.from_dict(data["bbox"]),
                "lines": [Line.from_dict(line) for line in data.get("lines", [])],
            }
        )
