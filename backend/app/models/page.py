import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))

    page_number: Mapped[int] = mapped_column(Integer)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    rotation: Mapped[int] = mapped_column(Integer, default=0)

    html_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    css_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    background_image: Mapped[str | None] = mapped_column(String(512), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="pages")
