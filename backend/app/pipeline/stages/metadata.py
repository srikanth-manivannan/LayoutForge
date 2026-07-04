import fitz

from app.core.enums import PipelineStage
from app.models.page import Page as PageRecord
from app.pipeline.context import PipelineContext
from app.pipeline.document import Document, DocumentMetadata
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.page import Page as PageElement
from app.pipeline.stages.base import Stage
from app.repositories.interfaces import IPageRepository, IProjectRepository


class MetadataStage(Stage):
    """Reads document-level metadata and per-page dimensions from the
    source PDF, populates the Internal Document Model, and persists the
    resulting Page rows so the project's page_count and per-page geometry
    are known before any extraction work begins."""

    def __init__(self, page_repository: IPageRepository, project_repository: IProjectRepository) -> None:
        self._page_repository = page_repository
        self._project_repository = project_repository

    @property
    def name(self) -> str:
        return PipelineStage.METADATA.value

    def run(self, context: PipelineContext) -> None:
        with fitz.open(context.source_pdf_path) as pdf:
            metadata = DocumentMetadata(
                title=pdf.metadata.get("title") or None,
                author=pdf.metadata.get("author") or None,
                subject=pdf.metadata.get("subject") or None,
                creator=pdf.metadata.get("creator") or None,
                producer=pdf.metadata.get("producer") or None,
                creation_date=pdf.metadata.get("creationDate") or None,
                modification_date=pdf.metadata.get("modDate") or None,
                page_count=pdf.page_count,
            )

            idm_pages: list[PageElement] = []
            page_records: list[PageRecord] = []
            for index, pdf_page in enumerate(pdf, start=1):
                rect = pdf_page.rect
                crop = pdf_page.cropbox
                media = pdf_page.mediabox
                idm_pages.append(
                    PageElement(
                        number=index,
                        width=rect.width,
                        height=rect.height,
                        rotation=pdf_page.rotation,
                        crop_box=BoundingBox(x=crop.x0, y=crop.y0, width=crop.width, height=crop.height),
                        media_box=BoundingBox(x=media.x0, y=media.y0, width=media.width, height=media.height),
                    )
                )
                page_records.append(
                    PageRecord(
                        project_id=context.project_id,
                        page_number=index,
                        width=rect.width,
                        height=rect.height,
                        rotation=pdf_page.rotation,
                    )
                )

        context.document = Document(project_id=context.project_id, metadata=metadata, pages=idm_pages)
        self._page_repository.bulk_create(page_records)

        project = self._project_repository.get(context.project_id)
        if project is not None:
            project.page_count = metadata.page_count
            self._project_repository.update(project)
