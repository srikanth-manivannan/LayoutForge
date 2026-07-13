from enum import Enum


class ProjectStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStage(str, Enum):
    """Canonical stage identifiers. Stage implementations expose their
    `name` as one of these `.value`s; the Job.stage column itself stays a
    plain string column so future plugin stages outside this enum remain
    representable without a migration."""

    VALIDATE = "validate"
    CREATE_PROJECT = "create_project"
    METADATA = "metadata"
    RENDER_BACKGROUND = "render_background"
    EXTRACT_FONTS = "extract_fonts"
    EXTRACT_IMAGES = "extract_images"
    EXTRACT_TEXT = "extract_text"
    NORMALIZE_IDM = "normalize_idm"
    RECONSTRUCT_TREE = "reconstruct_tree"
    VALIDATE_IDM = "validate_idm"
    QUALITY_ACCOUNTING = "quality_accounting"
    PERSIST_ASSETS = "persist_assets"
    GENERATE_CSS = "generate_css"
    GENERATE_HTML = "generate_html"
    GENERATE_SEMANTIC_HTML = "generate_semantic_html"
    GENERATE_MANIFEST = "generate_manifest"
    FINISH = "finish"


class AssetType(str, Enum):
    IMAGE = "image"
    FONT = "font"


class ReconstructionMode(str, Enum):
    """Adaptive-precision level at which an object is reconstructed
    (docs/design/typography). Every reconstructed object records the
    cheapest level that reproduced it within tolerance, so a document pays
    for precision only where the layout actually demands it:

    - WORD:  browser lays out the word at its pinned x (the default; most
             words need nothing more).
    - RUN:   a whole style run laid out together (reserved).
    - GLYPH: per-glyph placement — only words whose measured width/kern/
             baseline error exceeded tolerance escalate here (expensive;
             kept to the ~5% that need it, not the 100%).
    - SVG:   vector fallback when structure can't be reconstructed
             (math/complex art).
    """

    WORD = "word"
    RUN = "run"
    GLYPH = "glyph"
    SVG = "svg"


class ReconstructionReason(str, Enum):
    """WHY an object was reconstructed at its level — not just that it was
    (M1.6). Makes every escalation explainable and aggregatable into a
    document profile ("51,199 glyph words: 41k kerning, 6k ligatures, …"),
    which is diagnostic gold for improving the engine and for Validation.

    - NONE:        stayed at the default level; nothing needed.
    - WIDTH_ERROR: rendered wider than unkerned advances (tracking/spacing).
    - KERNING:     rendered narrower than unkerned advances (kern pulled in).
    - BASELINE:    baseline deviates from the line/grid.
    - LIGATURE:    contains ligature-forming sequences (ﬁ ﬂ ﬀ ﬃ ﬄ).
    - RTL:         right-to-left run (needs bidi/RTL reconstruction).
    - VERTICAL:    vertical writing mode (CJK).
    - ROTATION:    rotated run.
    - FONT_SUBSET: glyphs missing from the embedded subset (low coverage).
    - TRACKING:    genuine PDF character spacing (Tc), measured from actual
                    glyph advances (Rendering Accuracy v1, Issue 002B) — real
                    document typography, applied as letter-spacing, not a
                    width-fitting hack. May appear at WORD level (spacing
                    fully accounts for the residual) or GLYPH level (spacing
                    plus a further per-glyph correction).
    - UNKNOWN:     escalated/uncertain but unattributed (unmeasurable font).
    """

    NONE = "none"
    WIDTH_ERROR = "width_error"
    KERNING = "kerning"
    BASELINE = "baseline"
    LIGATURE = "ligature"
    RTL = "rtl"
    VERTICAL = "vertical"
    ROTATION = "rotation"
    FONT_SUBSET = "font_subset"
    TRACKING = "tracking"
    UNKNOWN = "unknown"
