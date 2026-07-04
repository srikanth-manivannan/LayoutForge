from dataclasses import dataclass

from app.core.enums import JobStatus
from app.events.base import Event


@dataclass
class ProjectCreated(Event):
    project_id: str
    name: str


@dataclass
class UploadCompleted(Event):
    project_id: str
    filename: str
    size_bytes: int


@dataclass
class JobStarted(Event):
    job_id: str
    project_id: str


@dataclass
class StageCompleted(Event):
    job_id: str
    stage: str
    duration_seconds: float


@dataclass
class JobFinished(Event):
    job_id: str
    status: JobStatus


@dataclass
class ProjectDeleted(Event):
    project_id: str
