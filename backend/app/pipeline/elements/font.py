from dataclasses import dataclass


@dataclass
class FontResource:
    """A font referenced by the document, decoupled from the PDF font
    object. `original_name` preserves the raw PDF font name (e.g. a
    subset-prefixed name like 'ABCDEF+Arial-Bold') for traceability."""

    id: str
    original_name: str
    family: str
    weight: str = "normal"  # "normal" | "bold"
    style: str = "normal"  # "normal" | "italic"
    embedded: bool = False
    subset: bool = False
    encoding: str | None = None
    filename: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "original_name": self.original_name,
            "family": self.family,
            "weight": self.weight,
            "style": self.style,
            "embedded": self.embedded,
            "subset": self.subset,
            "encoding": self.encoding,
            "filename": self.filename,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FontResource":
        return cls(**data)
