import hashlib
import logging
import time
import uuid

import fitz

from app.core.enums import AssetType, PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.elements.asset import AssetResource
from app.pipeline.stages.base import Stage
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")


class RenderBackgroundsStage(Stage):
    """Rasterizes each page to a background PNG at the configured DPI.
    Pixmap bytes are written to disk and released immediately after each
    page — only the lightweight IDM metadata (path, dimensions, hash)
    is retained, so memory use doesn't grow with page count.

    Text CAN be redacted from the raster before rendering (2026-07-13): the
    background is a proofing backdrop for art/photos/illustrations, never a
    second copy of the page's text — the Rich-IDM-driven HTML overlay is the
    only text layer. Without this, the raster's own baked-in PDF text and
    the HTML overlay's text render simultaneously, at very slightly
    different wrap points, producing an "overlapping paragraphs" illusion
    that is actually two independent, correctly-laid-out text layers stacked
    on each other (found via direct browser inspection — the HTML/CSS layer
    alone, isolated, renders with zero overlap). Redaction removes only the
    TEXT SHOWING content-stream operators inside each word's box — images
    and vector art are explicitly preserved (PDF_REDACT_IMAGE_NONE /
    PDF_REDACT_LINE_ART_NONE), and `cross_out=False` avoids drawing the
    default strike-through marks. This mutates only this stage's own
    in-memory `fitz.Document` (opened fresh from the source PDF and never
    saved back to disk) — extraction stages open their own independent
    instance and are unaffected.

    `redact_text` defaults OFF (2026-07-14): the renderer/Instruction
    Builder is mid-validation and must be verified against the ORIGINAL
    full-text background — changing the background asset at the same time
    as renderer fixes conflates two independent variables. The redaction
    code stays in place, gated, for re-enabling once the renderer is signed
    off (a separate milestone)."""

    def __init__(self, storage_service: StorageService, dpi: int, redact_text: bool = False) -> None:
        self._storage = storage_service
        self._dpi = dpi
        self._redact_text = redact_text

    @property
    def name(self) -> str:
        return PipelineStage.RENDER_BACKGROUND.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "MetadataStage must run before RenderBackgroundsStage"
        images_dir = self._storage.images_dir(context.project_id)
        zoom = self._dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        with fitz.open(context.source_pdf_path) as pdf:
            for index, pdf_page in enumerate(pdf, start=1):
                started = time.perf_counter()
                try:
                    if self._redact_text:
                        for word in pdf_page.get_text("words"):
                            x0, y0, x1, y1 = word[:4]
                            pdf_page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=None, cross_out=False)
                        if pdf_page.first_annot is not None:
                            pdf_page.apply_redactions(
                                images=fitz.PDF_REDACT_IMAGE_NONE,
                                graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                                text=fitz.PDF_REDACT_TEXT_REMOVE,
                            )
                    pixmap = pdf_page.get_pixmap(matrix=matrix)
                    image_bytes = pixmap.tobytes("png")
                    width, height = pixmap.width, pixmap.height
                    del pixmap
                except Exception:  # noqa: BLE001 - one bad page must not abort the whole document
                    logger.warning("page=%s render_background failed, leaving background unset", index, exc_info=True)
                    continue

                content_hash = hashlib.sha256(image_bytes).hexdigest()
                filename = f"page_{index:04d}_bg.png"
                destination = images_dir / filename
                destination.write_bytes(image_bytes)
                del image_bytes

                asset = AssetResource(
                    id=str(uuid.uuid4()),
                    type=AssetType.IMAGE.value,
                    filename=filename,
                    path=f"resources/images/{filename}",
                    hash=content_hash,
                    width=width,
                    height=height,
                    dpi=self._dpi,
                    color_space="RGB",
                    has_alpha=False,
                    referenced_pages=[index],
                )
                context.document.assets.append(asset)

                page = context.document.get_page(index)
                if page is not None:
                    page.background_image = asset.path

                logger.info(
                    "page=%s render_background dpi=%s size=%sx%s duration_ms=%.1f",
                    index,
                    self._dpi,
                    width,
                    height,
                    (time.perf_counter() - started) * 1000,
                )
