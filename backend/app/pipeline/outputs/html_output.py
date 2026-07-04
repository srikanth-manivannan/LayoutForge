from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.pipeline.context import PipelineContext
from app.pipeline.outputs.base import OutputPlugin
from app.pipeline.outputs.html_validator import HtmlValidator
from app.pipeline.outputs.paths import resource_href
from app.pipeline.outputs.renderers.image_renderer import ImageRenderer
from app.pipeline.outputs.renderers.page_renderer import PageRenderer
from app.pipeline.outputs.renderers.shape_renderer import ShapeRenderer
from app.pipeline.outputs.renderers.text_renderer import TextRenderer
from app.services.storage_service import StorageService

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class HtmlOutputPlugin(OutputPlugin):
    """Reads only the IDM — never PyMuPDF — and renders one semantic,
    layered HTML page per Page via Jinja2 templates. All href/src attributes
    use relative ../resources/... URLs so the output is self-contained: it
    renders identically opened from disk, served by the backend, or loaded
    into an iframe, without any per-renderer URL rewriting."""

    def __init__(self, storage_service: StorageService) -> None:
        self._storage = storage_service
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=select_autoescape(["html"])
        )
        self._validator = HtmlValidator()

    @property
    def name(self) -> str:
        return "html"

    def generate(self, context: PipelineContext) -> list[tuple[int, str]]:
        document = context.document
        assert document is not None, "Extraction stages must run before HtmlOutputPlugin"

        project_id = context.project_id
        pages_dir = self._storage.project_dir(project_id) / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        assets_by_id = {asset.id: asset for asset in document.assets}
        fonts_by_id = {font.id: font for font in document.fonts}
        page_renderer = PageRenderer(
            page_template=self._env.get_template("page.html"),
            text_renderer=TextRenderer(self._env.get_template("text_block.html"), fonts_by_id),
            image_renderer=ImageRenderer(self._env.get_template("image.html"), assets_by_id),
            shape_renderer=ShapeRenderer(self._env.get_template("shape.html")),
        )

        common_css_href = resource_href("resources/css/common.css")
        generated: list[tuple[int, str]] = []
        for page in document.pages:
            page_css_href = resource_href(f"resources/css/page_{page.number:04d}.css")
            background_src = resource_href(page.background_image) if page.background_image else None
            html = page_renderer.render(document, page, common_css_href, page_css_href, background_src)
            self._validator.validate(html, pages_dir)

            filename = f"page_{page.number:04d}.html"
            (pages_dir / filename).write_text(html, encoding="utf-8")
            generated.append((page.number, f"pages/{filename}"))

        return generated
