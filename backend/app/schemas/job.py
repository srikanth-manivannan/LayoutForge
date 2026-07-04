from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import JobStatus


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    status: JobStatus
    stage: str | None
    progress: int
    current_page: int
    total_pages: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
