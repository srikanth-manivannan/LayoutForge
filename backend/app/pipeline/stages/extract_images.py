import hashlib
import logging
import time
import uuid

import fitz

from app.core.enums import AssetType, PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.elements.asset import AssetResource
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.image import ImageElement
from app.pipeline.stages.base import Stage
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")


class ExtractImagesStage(Stage):
    """Extracts every embedded image, deduplicated first by PDF xref and
    then by content hash (so two different xrefs with identical bytes still
    collapse to one stored file), and records one ImageElement per
    placement so a repeated image isn't written to disk twice."""

    def __init__(self, storage_service: StorageService) -> None:
        self._storage = storage_service

    @property
    def name(self) -> str:
        return PipelineStage.EXTRACT_IMAGES.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "MetadataStage must run before ExtractImagesStage"
        images_dir = self._storage.images_dir(context.project_id)
        asset_by_xref: dict[int, AssetResource] = {}
        asset_by_hash: dict[str, AssetResource] = {a.hash: a for a in context.document.assets}

        with fitz.open(context.source_pdf_path) as pdf:
            for index, pdf_page in enumerate(pdf, start=1):
                started = time.perf_counter()
                placed = 0
                try:
                    page_images = pdf_page.get_images(full=True)
                except Exception:  # noqa: BLE001 - one bad page must not abort the whole document
                    logger.warning("page=%s extract_images failed", index, exc_info=True)
                    continue

                for image_info in page_images:
                    xref = image_info[0]
                    asset = asset_by_xref.get(xref)

                    if asset is None:
                        try:
                            extracted = pdf.extract_image(xref)
                        except Exception:  # noqa: BLE001 - skip an unreadable image, keep the page's text/others
                            logger.warning("page=%s xref=%s extract_image failed", index, xref, exc_info=True)
                            continue

                        image_bytes = extracted.get("image", b"")
                        content_hash = hashlib.sha256(image_bytes).hexdigest()
                        asset = asset_by_hash.get(content_hash)

                        if asset is None:
                            ext = extracted.get("ext", "png")
                            filename = f"{uuid.uuid4()}.{ext}"
                            (images_dir / filename).write_bytes(image_bytes)
                            asset = AssetResource(
                                id=str(uuid.uuid4()),
                                type=AssetType.IMAGE.value,
                                filename=filename,
                                path=f"resources/images/{filename}",
                                hash=content_hash,
                                width=extracted.get("width"),
                                height=extracted.get("height"),
                                color_space=str(extracted.get("colorspace", "")) or None,
                                has_alpha=bool(extracted.get("smask")),
                                original_object_id=str(xref),
                            )
                            context.document.assets.append(asset)
                            asset_by_hash[content_hash] = asset

                        del image_bytes
                        asset_by_xref[xref] = asset

                    if index not in asset.referenced_pages:
                        asset.referenced_pages.append(index)

                    page = context.document.get_page(index)
                    if page is None:
                        continue

                    try:
                        rects = pdf_page.get_image_rects(xref)
                    except Exception:  # noqa: BLE001 - placement lookup failure shouldn't drop the asset
                        rects = []

                    for rect in rects:
                        page.images.append(
                            ImageElement(
                                id=str(uuid.uuid4()),
                                asset_id=asset.id,
                                bbox=BoundingBox(x=rect.x0, y=rect.y0, width=rect.width, height=rect.height),
                            )
                        )
                        placed += 1

                logger.info(
                    "page=%s extract_images placed=%s duration_ms=%.1f",
                    index,
                    placed,
                    (time.perf_counter() - started) * 1000,
                )
