import logging
import time

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.outputs.html_output import HtmlOutputPlugin
from app.pipeline.stages.base import Stage
from app.repositories.interfaces import IPageRepository
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")


class GenerateHtmlStage(Stage):
    """Thin Stage wrapper around HtmlOutputPlugin: runs the plugin, then
    persists each page's html_path to the database."""

    def __init__(self, page_repository: IPageRepository, storage_service: StorageService) -> None:
        self._pages = page_repository
        self._plugin = HtmlOutputPlugin(storage_service)

    @property
    def name(self) -> str:
        return PipelineStage.GENERATE_HTML.value

    def run(self, context: PipelineContext) -> None:
        started = time.perf_counter()
        generated = self._plugin.generate(context)

        page_records = {p.page_number: p for p in self._pages.list_by_project(context.project_id)}
        for page_number, html_path in generated:
            record = page_records.get(page_number)
            if record is not None and record.html_path != html_path:
                record.html_path = html_path
                self._pages.update(record)

        logger.info(
            "project=%s generate_html pages=%s duration_ms=%.1f",
            context.project_id,
            len(generated),
            (time.perf_counter() - started) * 1000,
        )
