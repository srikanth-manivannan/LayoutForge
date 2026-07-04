from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import ProjectStatus


class ProjectCreateResponse(BaseModel):
    project_id: str
    job_id: str


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    filename: str
    page_count: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
