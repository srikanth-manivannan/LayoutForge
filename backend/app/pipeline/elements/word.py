from dataclasses import dataclass, field

from app.pipeline.elements.bbox import BoundingBox


@dataclass
class WordFragment:
    """The slice of one lexical word that lives in a single Run (ADR-011,
    Phase 2.6). A word never crosses a run boundary as a single unit; a
    genuinely mixed-style word (e.g. `theToad` with `the` small and `Toad`
    large, or `H` + subscript `2` + `O`) is represented as ordered fragments,
    each referencing its run by id — text is never duplicated or reordered."""

    run_id: str
    text: str

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict) -> "WordFragment":
        return cls(run_id=data["run_id"], text=data["text"])


@dataclass
class Word:
    """A lexical word reconstructed from the run stream (Phase 2.6) — NOT a
    PyMuPDF `get_text("words")` token (those are geometry hints only). A word
    is a maximal run of non-whitespace characters over a Line's runs; its
    `fragments` partition it by run so `"".join(f.text) == text` always holds.
    Words own geometry (x/width/baseline/bbox); runs own only style. Lives on
    the Line because a word may span several of its runs."""

    id: str
    text: str
    bbox: BoundingBox
    baseline_y: float = 0.0
    fragments: list[WordFragment] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "baseline_y": self.baseline_y,
            "fragments": [f.to_dict() for f in self.fragments],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Word":
        return cls(
            id=data["id"],
            text=data["text"],
            bbox=BoundingBox.from_dict(data["bbox"]),
            baseline_y=data.get("baseline_y", 0.0),
            fragments=[WordFragment.from_dict(f) for f in data.get("fragments", [])],
        )
