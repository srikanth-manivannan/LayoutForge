from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.pipeline.context import PipelineContext
from app.pipeline.outputs.base import OutputPlugin
from app.pipeline.outputs.html_validator import HtmlValidator
from app.pipeline.outputs.paths import resource_href
from app.pipeline.outputs.renderers.image_renderer import ImageRenderer
from app.pipeline.outputs.renderers.page_renderer import PageRenderer
from app.pipeline.outputs.renderers.shape_renderer import ShapeRenderer
from app.pipeline.rendering.html_compiler import compile_page_text_layer
from app.pipeline.rendering.render_tree import build_render_tree
from app.pipeline.rendering.tree_validator import validate_render_tree
from app.services.storage_service import StorageService

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class HtmlOutputPlugin(OutputPlugin):
    """Reads only the IDM — never PyMuPDF — and renders one layered HTML page
    per Page. Text renders through the Render Instruction Layer (RIL, the
    permanent rendering architecture): the Instruction Builder derives a
    deterministic Render Tree from the Rich IDM's paragraph tree, the
    RenderTreeValidator gates it, and a PURE compiler emits paragraph→line→
    run HTML. The tree lives only in `context.scratch` for the duration of
    output generation — derived, never canonical.

    All href/src attributes use relative ../resources/... URLs so the output
    is self-contained (disk, served, or iframe — identical rendering)."""

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
        page_renderer = PageRenderer(
            page_template=self._env.get_template("page.html"),
            image_renderer=ImageRenderer(self._env.get_template("image.html"), assets_by_id),
            shape_renderer=ShapeRenderer(self._env.get_template("shape.html")),
        )

        # Trees come from CssOutputPlugin (which already validated them).
        # Rebuilt only when the plugin is exercised standalone —
        # deterministic, so both paths agree.
        trees = context.scratch.get("ril_trees", {})

        common_css_href = resource_href("resources/css/common.css")
        generated: list[tuple[int, str]] = []
        for page in document.pages:
            if page.text_blocks and not page.regions:
                # Strict pipeline: the compiler consumes the Render Tree only.
                # Text without a reconstructed tree means ReconstructTreeStage
                # didn't run — that is a pipeline-order bug, never something
                # the renderer works around.
                raise RuntimeError(
                    f"page {page.number} has text but no reconstructed regions — "
                    "ReconstructTreeStage must run before HTML generation"
                )
            tree = trees.get(page.number)
            if tree is None:
                tree = build_render_tree(document, page)
                validate_render_tree(tree, page)  # Rule 6: gate before compiling
            text_fragments = compile_page_text_layer(tree)

            page_css_href = resource_href(f"resources/css/page_{page.number:04d}.css")
            background_src = resource_href(page.background_image) if page.background_image else None
            html = page_renderer.render(
                document, page, common_css_href, page_css_href, background_src, text_fragments
            )
            self._validator.validate(html, pages_dir)

            filename = f"page_{page.number:04d}.html"
            (pages_dir / filename).write_text(html, encoding="utf-8")
            generated.append((page.number, f"pages/{filename}"))

        return generated
