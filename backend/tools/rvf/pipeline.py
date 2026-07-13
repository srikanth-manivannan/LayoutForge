"""Run one PDF through the REAL production pipeline into an isolated
workspace (RVF). Uses the same stages as ConversionService so the harness
validates what ships — not a parallel re-implementation. One bad document
never aborts the corpus: failures are captured per document."""

import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401 - registers ORM models on Base.metadata
from app.core.config import Settings
from app.database.base import Base
from app.models.project import Project
from app.pipeline.context import PipelineContext
from app.pipeline.document import Document
from app.pipeline.engine import PipelineEngine
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
from app.pipeline.stages.render_backgrounds import RenderBackgroundsStage
from app.pipeline.stages.validate import ValidateStage
from app.pipeline.stages.validate_idm import ValidateRichIdmStage
from app.repositories.sqlite.asset_repository import SQLiteAssetRepository
from app.repositories.sqlite.page_repository import SQLitePageRepository
from app.repositories.sqlite.project_repository import SQLiteProjectRepository
from app.services.storage_service import StorageService


@dataclass
class RunArtifacts:
    name: str
    ok: bool
    document: Document | None = None
    project_dir: Path | None = None
    stage_timings: dict[str, float] = field(default_factory=dict)
    error: str | None = None


def run_pdf(pdf_path: Path, workspace_root: Path, *, dpi: int = 150, emit_debug: bool = True) -> RunArtifacts:
    name = pdf_path.name
    project_id = uuid.uuid4().hex
    settings = Settings(
        storage_root=workspace_root,
        preview_dpi=dpi,  # lower than print default for corpus throughput
        use_rich_tree=True,
        emit_debug_attributes=emit_debug,
    )
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        storage = StorageService(settings)
        storage.ensure_project_dirs(project_id)
        shutil.copyfile(pdf_path, storage.source_pdf_path(project_id))

        pages = SQLitePageRepository(session)
        projects = SQLiteProjectRepository(session)
        assets = SQLiteAssetRepository(session)
        projects.create(Project(id=project_id, name=name, filename=name, page_count=0))

        stages = [
            ValidateStage(),
            MetadataStage(pages, projects),
            RenderBackgroundsStage(storage, dpi=dpi),
            ExtractFontsStage(storage),
            ExtractImagesStage(storage),
            ExtractTextStage(),
            NormalizeIdmStage(storage),
            ReconstructTreeStage(),
            # Non-strict: record violations for the report without aborting the
            # corpus run (a document being invalid is data, not a crash).
            ValidateRichIdmStage(strict=False),
            QualityAccountingStage(),
            PersistAssetsStage(assets, pages, storage),
            GenerateCssStage(pages, storage),
            GenerateHtmlStage(pages, storage),
            GenerateSemanticHtmlStage(storage, enabled=True, emit_debug_attributes=emit_debug),
        ]
        pipeline = PipelineEngine(stages=stages)
        context = PipelineContext(
            job_id=uuid.uuid4().hex,
            project_id=project_id,
            source_pdf_path=storage.source_pdf_path(project_id),
            output_dir=storage.project_dir(project_id),
        )
        pipeline.run(context)
        timings = {m.stage: m.duration_seconds for m in pipeline.metrics}
        return RunArtifacts(
            name=name, ok=True, document=context.document,
            project_dir=storage.project_dir(project_id), stage_timings=timings,
        )
    except Exception as exc:  # noqa: BLE001 - a bad doc must not abort the corpus
        return RunArtifacts(name=name, ok=False, error=f"{type(exc).__name__}: {exc}")
    finally:
        session.close()
        engine.dispose()
