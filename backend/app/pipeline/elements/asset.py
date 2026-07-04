from dataclasses import dataclass, field


@dataclass
class AssetResource:
    """A unique binary asset (image or font file) referenced by the
    document, stored on disk exactly once and deduplicated by content hash.
    `referenced_pages` tracks every page that uses this asset, even though
    the file itself is written only once."""

    id: str
    type: str  # "image" | "font"
    filename: str
    path: str
    hash: str
    width: float | None = None
    height: float | None = None
    dpi: float | None = None
    color_space: str | None = None
    has_alpha: bool = False
    original_object_id: str | None = None
    referenced_pages: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "filename": self.filename,
            "path": self.path,
            "hash": self.hash,
            "width": self.width,
            "height": self.height,
            "dpi": self.dpi,
            "color_space": self.color_space,
            "has_alpha": self.has_alpha,
            "original_object_id": self.original_object_id,
            "referenced_pages": list(self.referenced_pages),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AssetResource":
        return cls(**{**data, "referenced_pages": list(data.get("referenced_pages", []))})
