from dataclasses import dataclass

from app.pipeline.elements.bbox import BoundingBox


@dataclass
class Glyph:
    """The leaf of the Rich IDM (ADR-001/011). One rendered glyph with the
    identity extraction captured — never re-derived downstream.

    Populated only where a word's metric residual proves per-glyph placement
    is needed (the GLYPH mode of the Adaptive Reconstruction Engine, M2), so
    a document never stores glyphs it does not need. `unicode` is the source
    of truth for character fidelity (ADR-010); `gid`/`cid` identify the glyph
    within its font; `advance` is the pen advance; `dx`/`dy` are placement
    offsets from the pen origin; `cluster` groups glyphs that map to one
    logical character (ligatures, marks)."""

    unicode: str
    gid: int = 0
    cid: int = 0
    advance: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    cluster: int = 0
    bbox: BoundingBox | None = None

    def to_dict(self) -> dict:
        return {
            "unicode": self.unicode,
            "gid": self.gid,
            "cid": self.cid,
            "advance": self.advance,
            "dx": self.dx,
            "dy": self.dy,
            "cluster": self.cluster,
            "bbox": self.bbox.to_dict() if self.bbox else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Glyph":
        return cls(
            **{
                **data,
                "bbox": BoundingBox.from_dict(data["bbox"]) if data.get("bbox") else None,
            }
        )
