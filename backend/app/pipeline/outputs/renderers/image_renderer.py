from jinja2 import Template

from app.pipeline.elements.asset import AssetResource
from app.pipeline.elements.image import ImageElement
from app.pipeline.outputs.paths import resource_href


class ImageRenderer:
    """Renders a single ImageElement placement into an INVISIBLE hotspot
    <div> — deliberately not a painted <img>.

    The page background raster already contains every image exactly as the
    PDF composited it (clip paths, soft masks, blend modes, draw order).
    Painting the raw extracted bitmap on top can only diverge from that
    ground truth — confirmed on real books: unclipped fragments doubled
    artwork, and one full-page unmasked image covered raster-only content
    entirely (user-reported "mirror text missing"). Same principle as the
    documented text-layer decision: the raster is the visual truth.

    The hotspot keeps the element's identity and geometry in the DOM
    (data-object-id → click-to-select → Properties, and the Phase 3 editor
    anchors), and `data-src` still points at the extracted asset so an
    editor can materialize the bitmap when the user actually edits it.
    Reads only the IDM — never touches the PDF."""

    def __init__(self, template: Template, assets_by_id: dict[str, AssetResource]) -> None:
        self._template = template
        self._assets_by_id = assets_by_id

    def render(self, page_number: int, image: ImageElement) -> str:
        asset = self._assets_by_id.get(image.asset_id)
        src = resource_href(asset.path) if asset else ""
        return self._template.render(
            id=f"img-{image.id}",
            object_id=image.id,
            page=page_number,
            asset_id=image.asset_id,
            rotation=image.rotation,
            src=src,
        )
