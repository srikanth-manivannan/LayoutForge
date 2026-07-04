import logging
import time

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.outputs.css_output import CssOutputPlugin
from app.pipeline.stages.base import Stage
from app.repositories.interfaces import IPageRepository
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")


class GenerateCssStage(Stage):
    """Thin Stage wrapper around CssOutputPlugin: runs the plugin, then
    persists each page's css_path to the database."""

    def __init__(self, page_repository: IPageRepository, storage_service: StorageService) -> None:
        self._pages = page_repository
        self._plugin = CssOutputPlugin(storage_service)

    @property
    def name(self) -> str:
        return PipelineStage.GENERATE_CSS.value

    def run(self, context: PipelineContext) -> None:
        started = time.perf_counter()
        generated = self._plugin.generate(context)

        page_records = {p.page_number: p for p in self._pages.list_by_project(context.project_id)}
        for page_number, css_path in generated:
            record = page_records.get(page_number)
            if record is not None and record.css_path != css_path:
                record.css_path = css_path
                self._pages.update(record)

        logger.info(
            "project=%s generate_css pages=%s duration_ms=%.1f",
            context.project_id,
            len(generated),
            (time.perf_counter() - started) * 1000,
        )
