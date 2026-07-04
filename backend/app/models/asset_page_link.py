import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AssetPageLink(Base):
    """Tracks every page that references a given (deduplicated) Asset,
    enabling 'referenced by' lookups without duplicating the asset file."""

    __tablename__ = "asset_page_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"))
    page_number: Mapped[int] = mapped_column(Integer)
