from dataclasses import dataclass

from app.pipeline.elements.bbox import BoundingBox


@dataclass
class ImageElement:
    """A single placement of an AssetResource (type="image") on a page.
    The same asset_id can appear in multiple ImageElements (one per page
    that places it) without the underlying file being duplicated."""

    id: str
    asset_id: str
    bbox: BoundingBox
    rotation: float = 0.0
    z_index: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "bbox": self.bbox.to_dict(),
            "rotation": self.rotation,
            "z_index": self.z_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageElement":
        return cls(**{**data, "bbox": BoundingBox.from_dict(data["bbox"])})
