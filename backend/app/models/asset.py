import uuid

from sqlalchemy import JSON, Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AssetType
from app.database.base import Base


class Asset(Base):
    """A unique binary asset (image or font file), deduplicated by hash
    within a project. `page_number` records where it was first encountered;
    every page (including repeats) is tracked via AssetPageLink."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))

    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[AssetType] = mapped_column(SAEnum(AssetType, values_callable=lambda e: [m.value for m in e]))
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(512))
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    hash: Mapped[str] = mapped_column(String(64))
    original_object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Type-specific extras (dpi/color_space/has_alpha for images;
    # family/weight/style/embedded/subset/encoding for fonts) — kept as a
    # JSON blob rather than a wide, mostly-empty column set.
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="assets")
