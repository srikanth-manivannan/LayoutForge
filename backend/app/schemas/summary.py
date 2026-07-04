from datetime import datetime

from pydantic import BaseModel

from app.core.enums import JobStatus, ProjectStatus


class StatisticsRead(BaseModel):
    page_count: int
    html_file_count: int
    css_file_count: int
    image_count: int
    font_count: int
    text_block_count: int
    disk_size_bytes: int


class ManifestPageRead(BaseModel):
    number: int
    width: float
    height: float
    rotation: int
    background_image: str | None


class ManifestFontRead(BaseModel):
    id: str
    family: str
    weight: str
    style: str
    embedded: bool


class ManifestAssetRead(BaseModel):
    id: str
    type: str
    filename: str
    path: str
    referenced_pages: list[int]


class ManifestRead(BaseModel):
    title: str | None
    author: str | None
    page_count: int
    pages: list[ManifestPageRead]
    fonts: list[ManifestFontRead]
    assets: list[ManifestAssetRead]


class HealthRead(BaseModel):
    storage_ok: bool
    idm_ok: bool
    all_pages_rendered: bool


class ProgressRead(BaseModel):
    job_id: str
    status: JobStatus
    stage: str | None
    progress: int
    current_page: int
    total_pages: int
    error_message: str | None


class ProjectSummaryProjectRead(BaseModel):
    id: str
    name: str
    filename: str
    page_count: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectSummary(BaseModel):
    project: ProjectSummaryProjectRead
    statistics: StatisticsRead
    manifest: ManifestRead | None
    health: HealthRead
    progress: ProgressRead | None
    warnings: list[str]
    recent_logs: list[str]
