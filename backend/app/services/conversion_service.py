import logging
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.enums import JobStatus, ProjectStatus
from app.events.dispatcher import EventDispatcher
from app.events.events import JobFinished, JobStarted, StageCompleted
from app.pipeline.context import PipelineContext
from app.pipeline.engine import PipelineEngine, PipelineStageError, StageProgress
from app.pipeline.stages.extract_fonts import ExtractFontsStage
from app.pipeline.stages.extract_images import ExtractImagesStage
from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.generate_css import GenerateCssStage
from app.pipeline.stages.generate_html import GenerateHtmlStage
from app.pipeline.stages.generate_semantic_html import GenerateSemanticHtmlStage
from app.pipeline.stages.metadata import MetadataStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.persist_assets import PersistAssetsStage
from app.pipeline.stages.quality_accounting import QualityAccountingStage
from app.pipeline.stages.reconstruct_tree import ReconstructTreeStage
from app.pipeline.stages.validate_idm import ValidateRichIdmStage
from app.pipeline.stages.render_backgrounds import RenderBackgroundsStage
from app.pipeline.stages.validate import ValidateStage
from app.repositories.interfaces import IAssetRepository, IJobRepository, IPageRepository, IProjectRepository
from app.services.conversion_report import build_report, write_report
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")


class ConversionService:
    """Builds and runs the PipelineEngine for a job. Each Phase 1 task adds
    its stages to `_build_stages`; the engine, context, and job bookkeeping
    here stay unchanged as the stage list grows."""

    def __init__(
        self,
        job_repository: IJobRepository,
        project_repository: IProjectRepository,
        page_repository: IPageRepository,
        asset_repository: IAssetRepository,
        storage_service: StorageService,
        settings: Settings,
        dispatcher: EventDispatcher,
    ) -> None:
        self._jobs = job_repository
        self._projects = project_repository
        self._pages = page_repository
        self._assets = asset_repository
        self._storage = storage_service
        self._settings = settings
        self._dispatcher = dispatcher

    def _build_stages(self) -> list:
        return [
            ValidateStage(),
            MetadataStage(self._pages, self._projects),
            RenderBackgroundsStage(
                self._storage, dpi=self._settings.preview_dpi,
                redact_text=self._settings.redact_background_text,
            ),
            ExtractFontsStage(self._storage),
            ExtractImagesStage(self._storage),
            ExtractTextStage(),
            NormalizeIdmStage(self._storage),
            ReconstructTreeStage(),
            # Advisory unless semantic rendering is on: surfaces model defects
            # without blocking the legacy default output (Phase 2.5).
            ValidateRichIdmStage(strict=self._settings.use_rich_tree),
            QualityAccountingStage(),  # measured quality (Phase 2.7)
            PersistAssetsStage(self._assets, self._pages, self._storage),
            # RIL: GenerateCss builds+validates the Render Trees (scratch,
            # derived — discarded after output) and emits the Style Registry;
            # GenerateHtml compiles the same trees. CSS first so the HTML
            # validator finds every linked stylesheet on disk.
            GenerateCssStage(self._pages, self._storage),
            GenerateHtmlStage(self._pages, self._storage),
            GenerateSemanticHtmlStage(
                self._storage,
                enabled=self._settings.use_rich_tree,
                emit_debug_attributes=self._settings.emit_debug_attributes,
            ),
        ]

    def run_pipeline(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            logger.error("job=%s not found, aborting pipeline run", job_id)
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        self._jobs.update(job)
        self._set_project_status(job.project_id, ProjectStatus.PROCESSING)
        self._dispatcher.publish(JobStarted(job_id=job.id, project_id=job.project_id))

        context = PipelineContext(
            job_id=job.id,
            project_id=job.project_id,
            source_pdf_path=self._storage.source_pdf_path(job.project_id),
            output_dir=self._storage.project_dir(job.project_id),
        )

        def on_progress(progress: StageProgress) -> None:
            job.stage = progress.stage
            job.progress = progress.progress
            self._jobs.update(job)
            self._dispatcher.publish(
                StageCompleted(job_id=job.id, stage=progress.stage, duration_seconds=progress.duration_seconds)
            )

        engine = PipelineEngine(stages=self._build_stages(), on_progress=on_progress)

        try:
            engine.run(context)
        except PipelineStageError as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            self._jobs.update(job)
            self._set_project_status(job.project_id, ProjectStatus.FAILED)
            self._dispatcher.publish(JobFinished(job_id=job.id, status=JobStatus.FAILED))
            return

        # Conversion report (M1.7): reconstruction analytics + per-stage
        # timing/memory. Best-effort — never fail a completed conversion.
        if context.document is not None:
            report = build_report(context.document, engine.metrics)
            write_report(report, self._storage.project_dir(job.project_id))

        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.now(timezone.utc)
        self._jobs.update(job)
        self._set_project_status(job.project_id, ProjectStatus.READY)
        self._dispatcher.publish(JobFinished(job_id=job.id, status=JobStatus.COMPLETED))

    def _set_project_status(self, project_id: str, status: ProjectStatus) -> None:
        project = self._projects.get(project_id)
        if project is not None:
            project.status = status
            self._projects.update(project)
