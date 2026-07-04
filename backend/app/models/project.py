import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ProjectStatus
from app.database.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, values_callable=lambda e: [m.value for m in e]),
        default=ProjectStatus.CREATED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    jobs: Mapped[list["Job"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    pages: Mapped[list["Page"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
