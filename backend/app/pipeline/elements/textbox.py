from dataclasses import dataclass, field

from app.pipeline.elements.bbox import BoundingBox


@dataclass
class WordBox:
    """One word with the exact x-extent the PDF laid it out at
    (`page.get_text("words")`). This is the "run/word" level of the
    typography model: pinning each word to its own x0 makes cross-word
    drift structurally impossible — a word carries its internal kerning in
    its own width, and nothing accumulates across the line. `letter_spacing`
    is fitted (NormalizeIdmStage) so the word's rendered width equals
    `width`. `x` is page-space; the renderer offsets it by the line's x."""

    text: str
    x: float
    width: float
    baseline_y: float
    font_id: str | None = None
    font_size: float = 0.0
    color: str = "#000000"
    letter_spacing: float = 0.0
    # Adaptive Reconstruction (M1.5/M1.6/M1.7): the level this word was
    # reconstructed at (`mode`), WHY it escalated (`reason`), and an internal
    # engineering `reconstruction_confidence` in [0,1] that the current
    # reconstruction reproduces the word (NOT a user-facing score — used for
    # decisions and diagnostics; named specifically so it never collides
    # with future OCR/AI/table/reading-order/accessibility confidences), and
    # the residual `width_error` (px). Written from a frozen
    # ReconstructionDecision (see typography.adaptive_reconstruction).
    mode: str = "word"
    reason: str = "none"
    reconstruction_confidence: float = 1.0
    width_error: float = 0.0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "x": self.x,
            "width": self.width,
            "baseline_y": self.baseline_y,
            "font_id": self.font_id,
            "font_size": self.font_size,
            "color": self.color,
            "letter_spacing": self.letter_spacing,
            "mode": self.mode,
            "reason": self.reason,
            "reconstruction_confidence": self.reconstruction_confidence,
            "width_error": self.width_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WordBox":
        # Tolerate the pre-M1.7 `confidence` key from older idm.json files.
        if "confidence" in data and "reconstruction_confidence" not in data:
            data = {**data, "reconstruction_confidence": data.pop("confidence")}
        return cls(**data)


@dataclass
class TextSpan:
    """One styled run within a TextBlock. PDF lines routinely mix styles
    mid-run (e.g. a sentence with two or three differently-colored words,
    confirmed in practice: a single line with 3 spans in 3 different
    colors) — flattening to the line's first span silently drops that
    styling. `spans` is the source of truth for rendering; TextBlock's own
    text/font_id/font_size/color fields mirror the first span purely so
    code that only cares about line-level approximations (search,
    plain-text export) doesn't need to special-case an empty spans list."""

    text: str
    font_id: str | None = None
    font_size: float = 0.0
    color: str = "#000000"

    def to_dict(self) -> dict:
        return {"text": self.text, "font_id": self.font_id, "font_size": self.font_size, "color": self.color}

    @classmethod
    def from_dict(cls, data: dict) -> "TextSpan":
        return cls(**data)


@dataclass
class TextBlock:
    """A normalized line of text. PyMuPDF's "block > line > span" hierarchy
    is flattened to one TextBlock per line — but each line's spans (one
    per style run) are preserved in `spans` rather than collapsed to a
    single style, since real-world PDFs mix colors/fonts within a line
    often enough that collapsing them is visibly wrong (e.g. "Monkey
    Pen's" in blue, "Vision is to..." in black, "free children's" in
    orange — all one PDF line). `text`/`font_id`/`font_size`/`color` below
    mirror the first span for line-level approximations.

    `origin`/`ascender`/`descender` are preserved from PyMuPDF's span dict
    (ascender/descender as fractions of font_size, per PyMuPDF convention)
    because `bbox` alone is not enough to reproduce PDF baseline
    positioning in HTML — see docs/25_FUTURE_ENHANCEMENTS.md "Layout
    Accuracy" notes. char_spacing/word_spacing/horizontal_scale/render_mode
    are NOT currently extracted: PyMuPDF's high-level get_text("dict") does
    not expose them; doing so would require parsing raw content-stream
    operators (Tc/Tw/Tz/Tr), which is out of scope for now. The fields
    exist with neutral defaults so the shape is ready when that lands."""

    id: str
    page: int
    bbox: BoundingBox
    text: str
    font_id: str | None = None
    font_size: float = 0.0
    color: str = "#000000"
    alignment: str = "left"  # "left" | "center" | "right" | "justify"
    rotation: float = 0.0
    reading_order: int = 0
    line_height: float = 0.0
    letter_spacing: float = 0.0
    word_spacing: float = 0.0
    writing_direction: str = "ltr"  # "ltr" | "rtl"
    origin_x: float = 0.0
    origin_y: float = 0.0
    ascender: float = 0.8  # fraction of font_size, PyMuPDF convention
    descender: float = -0.2  # fraction of font_size, PyMuPDF convention
    horizontal_scale: float = 1.0  # not yet extracted; reserved for Tz
    render_mode: int = 0  # not yet extracted; reserved for Tr (0 = fill)
    spans: list[TextSpan] = field(default_factory=list)
    # Word-level boxes (typography Milestone 1). When present, the renderer
    # word-pins the line — see WordBox. Empty for lines where word boxes
    # couldn't be resolved; the renderer falls back to span/line rendering.
    words: list[WordBox] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "page": self.page,
            "bbox": self.bbox.to_dict(),
            "text": self.text,
            "font_id": self.font_id,
            "font_size": self.font_size,
            "color": self.color,
            "alignment": self.alignment,
            "rotation": self.rotation,
            "reading_order": self.reading_order,
            "line_height": self.line_height,
            "letter_spacing": self.letter_spacing,
            "word_spacing": self.word_spacing,
            "writing_direction": self.writing_direction,
            "origin_x": self.origin_x,
            "origin_y": self.origin_y,
            "ascender": self.ascender,
            "descender": self.descender,
            "horizontal_scale": self.horizontal_scale,
            "render_mode": self.render_mode,
            "spans": [s.to_dict() for s in self.spans],
            "words": [w.to_dict() for w in self.words],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TextBlock":
        return cls(
            **{
                **data,
                "bbox": BoundingBox.from_dict(data["bbox"]),
                "spans": [TextSpan.from_dict(s) for s in data.get("spans", [])],
                "words": [WordBox.from_dict(w) for w in data.get("words", [])],
            }
        )
