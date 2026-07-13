"""WriterContext + feature flags (ADR-011, Phase 3).

One context object flows into every writer instead of a growing list of
boolean parameters. It carries the target format, the feature flags, the LFS
version the output conforms to, and the (optional) product edition, plus a
resolved `fonts_by_id` map so writers never re-derive it.
"""

from dataclasses import dataclass, field
from enum import Enum

from app.pipeline.document import Document
from app.pipeline.elements.font import FontResource


class Target(str, Enum):
    """Output formats. HTML is implemented; the rest are reserved seams so a
    new format is added as a Writer, never by touching the engines (ADR-005)."""

    HTML = "html"  # semantic, reflowable
    FIXED_LAYOUT = "fixed_layout"  # absolutely-positioned, raster-backed
    EPUB = "epub"
    XML = "xml"
    PML = "pml"


@dataclass(frozen=True)
class FeatureFlags:
    """Named capabilities, replacing scattered boolean args. Defaults describe
    the semantic HTML writer's normal operation; a Fixed-Layout or debugging
    run flips only what it needs."""

    use_rich_tree: bool = True          # render page.regions, not legacy text_blocks
    emit_semantic_html: bool = True     # <p>/<span> semantics vs positioned boxes
    emit_paragraph_metrics: bool = True # line-height/align/indent on the paragraph
    emit_stable_ids: bool = True        # data-object-id on every node
    emit_accessibility: bool = False    # ARIA/roles (Phase 5, reserved)
    emit_debug_attributes: bool = False # data-confidence/data-signals/geometry


@dataclass
class WriterContext:
    document: Document
    target: Target = Target.HTML
    flags: FeatureFlags = field(default_factory=FeatureFlags)
    lfs_version: str = "1.0"
    edition: str | None = None
    fonts_by_id: dict[str, FontResource] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        document: Document,
        target: Target = Target.HTML,
        flags: FeatureFlags | None = None,
        edition: str | None = None,
    ) -> "WriterContext":
        return cls(
            document=document,
            target=target,
            flags=flags or FeatureFlags(),
            edition=edition,
            fonts_by_id={font.id: font for font in document.fonts},
        )
