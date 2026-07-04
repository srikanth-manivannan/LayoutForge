from dataclasses import dataclass


@dataclass
class BoundingBox:
    """A page-space rectangle shared by every positioned IDM element."""

    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, data: dict) -> "BoundingBox":
        return cls(x=data["x"], y=data["y"], width=data["width"], height=data["height"])
