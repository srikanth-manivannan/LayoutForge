from pydantic import BaseModel, ConfigDict


class PageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    width: float
    height: float
    rotation: int
    html_path: str | None
    css_path: str | None
    background_image: str | None
