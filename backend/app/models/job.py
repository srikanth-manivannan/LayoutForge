import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import JobStatus
from app.database.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))

    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, values_callable=lambda e: [m.value for m in e]),
        default=JobStatus.QUEUED,
    )
    # Stage names come from app.core.enums.PipelineStage.value for built-in
    # stages, but this stays a plain string so future plugin stages outside
    # that enum remain representable without a migration.
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # written by the pipeline engine, never derived
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="jobs")
