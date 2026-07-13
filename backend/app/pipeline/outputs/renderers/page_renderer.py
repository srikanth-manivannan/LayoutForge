from jinja2 import Template

from app.pipeline.document import Document
from app.pipeline.elements.page import Page
from app.pipeline.outputs.renderers.image_renderer import ImageRenderer
from app.pipeline.outputs.renderers.shape_renderer import ShapeRenderer


class PageRenderer:
    """Assembles one page: background + image/shape renderers + the text
    layer fragments compiled by the RIL HTML compiler (passed in — this
    class never touches text models). All URLs are pre-computed by the
    caller (HtmlOutputPlugin); this renderer applies no URL logic itself."""

    def __init__(
        self,
        page_template: Template,
        image_renderer: ImageRenderer,
        shape_renderer: ShapeRenderer,
    ) -> None:
        self._page_template = page_template
        self._image_renderer = image_renderer
        self._shape_renderer = shape_renderer

    def render(
        self,
        document: Document,
        page: Page,
        common_css_href: str,
        page_css_href: str,
        background_src: str | None,
        text_fragments: list[str],
    ) -> str:
        return self._page_template.render(
            page_id=f"{document.project_id}-{page.number}",
            page_number=page.number,
            width=page.width,
            height=page.height,
            rotation=page.rotation,
            common_css_href=common_css_href,
            page_css_href=page_css_href,
            background_src=background_src,
            image_fragments=[self._image_renderer.render(page.number, image) for image in page.images],
            shape_fragments=[self._shape_renderer.render(page.number, shape) for shape in page.shapes],
            text_fragments=text_fragments,
        )
