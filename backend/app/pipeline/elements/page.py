from dataclasses import dataclass, field

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.image import ImageElement
from app.pipeline.elements.region import Region
from app.pipeline.elements.shape import ShapeElement
from app.pipeline.elements.textbox import TextBlock


@dataclass
class Page:
    """A single page within the Internal Document Model. Once Task 3
    completes, everything an output plugin needs to render this page lives
    here — it never needs to reopen the source PDF."""

    number: int
    width: float
    height: float
    rotation: int = 0
    crop_box: BoundingBox | None = None
    media_box: BoundingBox | None = None
    background_image: str | None = None
    text_blocks: list[TextBlock] = field(default_factory=list)
    images: list[ImageElement] = field(default_factory=list)
    shapes: list[ShapeElement] = field(default_factory=list)
    fonts_used: list[str] = field(default_factory=list)
    # Rich IDM (ADR-011). The typographic tree built by Typography/Semantic
    # reconstruction, held in parallel with `text_blocks` during the phased
    # migration. Empty until a reconstruction stage populates it; the
    # renderer prefers it when present and falls back to `text_blocks`.
    regions: list[Region] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "crop_box": self.crop_box.to_dict() if self.crop_box else None,
            "media_box": self.media_box.to_dict() if self.media_box else None,
            "background_image": self.background_image,
            "text_blocks": [t.to_dict() for t in self.text_blocks],
            "images": [i.to_dict() for i in self.images],
            "shapes": [s.to_dict() for s in self.shapes],
            "fonts_used": list(self.fonts_used),
            "regions": [r.to_dict() for r in self.regions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Page":
        return cls(
            number=data["number"],
            width=data["width"],
            height=data["height"],
            rotation=data.get("rotation", 0),
            crop_box=BoundingBox.from_dict(data["crop_box"]) if data.get("crop_box") else None,
            media_box=BoundingBox.from_dict(data["media_box"]) if data.get("media_box") else None,
            background_image=data.get("background_image"),
            text_blocks=[TextBlock.from_dict(t) for t in data.get("text_blocks", [])],
            images=[ImageElement.from_dict(i) for i in data.get("images", [])],
            shapes=[ShapeElement.from_dict(s) for s in data.get("shapes", [])],
            fonts_used=list(data.get("fonts_used", [])),
            regions=[Region.from_dict(r) for r in data.get("regions", [])],
        )
