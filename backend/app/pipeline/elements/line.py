from dataclasses import dataclass, field

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.run import Run
from app.pipeline.elements.word import Word


@dataclass
class Line:
    """One typographic line within a Paragraph (ADR-001/011). A Line owns its
    vertical placement (`baseline_y`, `ascent`, `descent`, `leading`), its
    ordered style `runs`, and its lexical `words` (Phase 2.6 — reconstructed
    from the runs, since a word may span several runs). It deliberately does
    NOT own line-height, alignment, or spacing — those are paragraph
    properties (see Paragraph). `line_index` is the line's position within its
    paragraph (0-based)."""

    id: str
    bbox: BoundingBox
    baseline_y: float = 0.0
    ascent: float = 0.0
    descent: float = 0.0
    leading: float = 0.0
    line_index: int = 0
    runs: list[Run] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bbox": self.bbox.to_dict(),
            "baseline_y": self.baseline_y,
            "ascent": self.ascent,
            "descent": self.descent,
            "leading": self.leading,
            "line_index": self.line_index,
            "runs": [r.to_dict() for r in self.runs],
            "words": [w.to_dict() for w in self.words],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Line":
        return cls(
            **{
                **data,
                "bbox": BoundingBox.from_dict(data["bbox"]),
                "runs": [Run.from_dict(r) for r in data.get("runs", [])],
                "words": [Word.from_dict(w) for w in data.get("words", [])],
            }
        )
