from jinja2 import Template

from app.pipeline.elements.shape import ShapeElement


class ShapeRenderer:
    """Renders a single ShapeElement into a placeholder fragment. No
    extraction stage populates Page.shapes yet (out of scope for Task 3),
    so this renderer exists for forward compatibility and is exercised by
    tests with hand-built ShapeElements, not by real extraction output."""

    def __init__(self, template: Template) -> None:
        self._template = template

    def render(self, page_number: int, shape: ShapeElement) -> str:
        return self._template.render(
            id=f"shape-{shape.id}", object_id=shape.id, page=page_number, kind=shape.kind
        )
