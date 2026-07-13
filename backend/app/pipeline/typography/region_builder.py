"""Region Builder (ADR-011, Phase 2).

Regions are the page-aware layer: headers, footers, margin notes, footnotes,
sidebars, captions, and columns are all Regions, and paragraphs do not know
about pages — Regions do. This keeps page-level reading order out of the
Paragraph Builder.

Phase 2 emits a single `body` Region holding every paragraph in reading
order. Header/footer/margin/column detection are separate work packages
(M3 WP3) that add Regions here; isolating this stage means they land without
touching Run/Line/Paragraph building.
"""

import uuid

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.paragraph import Paragraph
from app.pipeline.elements.region import Region


def build_regions(paragraphs: list[Paragraph]) -> list[Region]:
    if not paragraphs:
        return []
    xs = [p.bbox.x for p in paragraphs]
    ys = [p.bbox.y for p in paragraphs]
    rights = [p.bbox.x + p.bbox.width for p in paragraphs]
    bottoms = [p.bbox.y + p.bbox.height for p in paragraphs]
    left, top = min(xs), min(ys)
    bbox = BoundingBox(x=left, y=top, width=max(rights) - left, height=max(bottoms) - top)
    return [
        Region(
            id=str(uuid.uuid4()),
            bbox=bbox,
            kind="body",
            column_index=0,
            reading_order=0,
            paragraphs=paragraphs,
        )
    ]
