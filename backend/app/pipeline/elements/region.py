from dataclasses import dataclass, field

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.paragraph import Paragraph


@dataclass
class Region:
    """A reading area on a page (ADR-001/011): a body column, header, footer,
    margin note, or sidebar. Regions carry reading order so multi-column and
    running-head/foot layouts serialize in the correct sequence (M3 WP3).

    For now a Region holds `paragraphs`. Table/List/Figure blocks join here
    as sibling collections in their milestones (M3 WP2/WP4/WP5); keeping the
    text spine explicit avoids premature union machinery while staying
    additive."""

    id: str
    bbox: BoundingBox
    kind: str = "body"  # "body" | "column" | "header" | "footer" | "margin" | "sidebar"
    column_index: int = 0
    reading_order: int = 0
    paragraphs: list[Paragraph] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bbox": self.bbox.to_dict(),
            "kind": self.kind,
            "column_index": self.column_index,
            "reading_order": self.reading_order,
            "paragraphs": [p.to_dict() for p in self.paragraphs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Region":
        return cls(
            **{
                **data,
                "bbox": BoundingBox.from_dict(data["bbox"]),
                "paragraphs": [Paragraph.from_dict(p) for p in data.get("paragraphs", [])],
            }
        )
