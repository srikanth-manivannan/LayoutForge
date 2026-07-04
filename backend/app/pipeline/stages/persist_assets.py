import hashlib
import logging
import time

from app.core.enums import AssetType, PipelineStage
from app.models.asset import Asset
from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import Stage
from app.repositories.interfaces import IAssetRepository, IPageRepository
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")


class PersistAssetsStage(Stage):
    """The final extraction-phase stage: writes every IDM asset to the
    assets/asset_page_links tables (deduplicated by content hash), updates
    each Page row's background_image, and serializes the complete IDM to
    storage/projects/{id}/idm.json. After this stage, any future stage or
    output plugin can fully reconstruct the Document from disk + DB alone —
    it never needs to reopen the source PDF."""

    def __init__(
        self, asset_repository: IAssetRepository, page_repository: IPageRepository, storage_service: StorageService
    ) -> None:
        self._assets = asset_repository
        self._pages = page_repository
        self._storage = storage_service

    @property
    def name(self) -> str:
        return PipelineStage.PERSIST_ASSETS.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "Extraction stages must run before PersistAssetsStage"
        started = time.perf_counter()

        for asset in context.document.assets:
            record = self._assets.get_by_hash(context.project_id, asset.hash)
            if record is None:
                record = self._assets.create(
                    Asset(
                        project_id=context.project_id,
                        page_number=asset.referenced_pages[0] if asset.referenced_pages else None,
                        type=AssetType(asset.type),
                        filename=asset.filename,
                        path=asset.path,
                        width=asset.width,
                        height=asset.height,
                        hash=asset.hash,
                        original_object_id=asset.original_object_id,
                        details={"dpi": asset.dpi, "color_space": asset.color_space, "has_alpha": asset.has_alpha},
                    )
                )
            for page_number in asset.referenced_pages:
                self._assets.add_page_reference(record.id, page_number)

        fonts_dir = self._storage.fonts_dir(context.project_id)
        for font in context.document.fonts:
            if not font.filename:
                continue
            font_bytes = (fonts_dir / font.filename).read_bytes()
            content_hash = hashlib.sha256(font_bytes).hexdigest()
            if self._assets.get_by_hash(context.project_id, content_hash) is None:
                self._assets.create(
                    Asset(
                        project_id=context.project_id,
                        page_number=None,
                        type=AssetType.FONT,
                        filename=font.filename,
                        path=f"resources/fonts/{font.filename}",
                        hash=content_hash,
                        details={
                            "family": font.family,
                            "weight": font.weight,
                            "style": font.style,
                            "embedded": font.embedded,
                            "subset": font.subset,
                            "encoding": font.encoding,
                        },
                    )
                )

        page_records = {p.page_number: p for p in self._pages.list_by_project(context.project_id)}
        for idm_page in context.document.pages:
            record = page_records.get(idm_page.number)
            if record is not None and record.background_image != idm_page.background_image:
                record.background_image = idm_page.background_image
                self._pages.update(record)

        idm_path = self._storage.save_idm(context.document)

        logger.info(
            "project=%s persist_assets assets=%s pages=%s idm_path=%s duration_ms=%.1f",
            context.project_id,
            len(context.document.assets),
            len(context.document.pages),
            idm_path,
            (time.perf_counter() - started) * 1000,
        )
