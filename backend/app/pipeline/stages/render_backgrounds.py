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
    is retained, so memory use doesn't grow with page count."""

    def __init__(self, storage_service: StorageService, dpi: int) -> None:
        self._storage = storage_service
        self._dpi = dpi

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
