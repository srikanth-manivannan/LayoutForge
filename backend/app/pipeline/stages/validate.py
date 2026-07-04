import fitz

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import Stage


class ValidateStage(Stage):
    """Defense-in-depth re-validation that the stored source PDF still
    opens cleanly. The authoritative validation (extension/MIME/structure)
    already ran synchronously in ProjectService before the project and job
    were created; this stage protects the pipeline itself from a source
    file that was moved, corrupted, or replaced after upload."""

    @property
    def name(self) -> str:
        return PipelineStage.VALIDATE.value

    def run(self, context: PipelineContext) -> None:
        with fitz.open(context.source_pdf_path) as document:
            if document.needs_pass:
                raise ValueError("Source PDF is password-protected")
