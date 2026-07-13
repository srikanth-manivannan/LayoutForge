"""GenerateSemanticHtml stage (Phase 3b): flag-gated parallel output. Off by
default (no files, no production change); on, it writes the semantic tree +
shared deduplicated CSS."""

from pathlib import Path

from app.core.config import Settings
from app.pipeline.context import PipelineContext
from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.stages.generate_semantic_html import GenerateSemanticHtmlStage
from app.pipeline.typography.line_builder import build_line
from app.pipeline.typography.paragraph_builder import build_paragraphs
from app.pipeline.typography.region_builder import build_regions
from app.services.storage_service import StorageService


def _context(tmp_path: Path) -> tuple[PipelineContext, StorageService]:
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    fonts_by_id = {f.id: f for f in fonts}
    block = TextBlock(
        id="b1", page=1, bbox=BoundingBox(50.0, 100.0, 300.0, 12.0),
        text="Hello world", origin_y=110.0, line_height=14.0, font_size=12.0,
        spans=[TextSpan(text="Hello world", font_id="f1", font_size=12.0, color="#000000")],
    )
    lines = [build_line(block, 0, fonts_by_id)]
    page = Page(number=1, width=600.0, height=800.0, text_blocks=[block],
                regions=build_regions(build_paragraphs(lines, fonts_by_id)))
    doc = Document(project_id="proj", pages=[page], fonts=fonts)

    storage = StorageService(Settings(storage_root=tmp_path))
    storage.ensure_project_dirs("proj")
    ctx = PipelineContext(job_id="j", project_id="proj", source_pdf_path=None, output_dir=None)
    ctx.document = doc
    return ctx, storage


def test_disabled_writes_nothing(tmp_path: Path) -> None:
    ctx, storage = _context(tmp_path)
    GenerateSemanticHtmlStage(storage, enabled=False).run(ctx)
    assert not (storage.project_dir("proj") / "pages_semantic").exists()


def test_enabled_writes_pages_and_shared_css(tmp_path: Path) -> None:
    ctx, storage = _context(tmp_path)
    GenerateSemanticHtmlStage(storage, enabled=True).run(ctx)

    out = storage.project_dir("proj") / "pages_semantic"
    page_html = (out / "page_0001.html").read_text(encoding="utf-8")
    assert "lf-paragraph" in page_html and "Hello world" in page_html
    assert (out / "semantic.css").exists()
