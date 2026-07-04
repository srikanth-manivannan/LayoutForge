from dataclasses import dataclass, field

from app.pipeline.elements.bbox import BoundingBox


@dataclass
class ShapeElement:
    """A vector shape (rect/line/path fill or stroke) on a page. No
    extraction stage populates this yet (out of scope for Task 3); the
    model exists so Page's shape: list[...] field has a defined type for
    when vector-graphics extraction is added."""

    id: str
    kind: str  # "rect" | "line" | "path"
    bbox: BoundingBox
    fill_color: str | None = None
    stroke_color: str | None = None
    stroke_width: float = 0.0
    z_index: int = 0
    points: list[tuple[float, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "bbox": self.bbox.to_dict(),
            "fill_color": self.fill_color,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "z_index": self.z_index,
            "points": [list(p) for p in self.points],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShapeElement":
        return cls(
            **{
                **data,
                "bbox": BoundingBox.from_dict(data["bbox"]),
                "points": [tuple(p) for p in data.get("points", [])],
            }
        )
