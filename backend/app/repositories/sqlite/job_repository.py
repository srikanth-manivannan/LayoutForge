from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories.interfaces import IJobRepository


class SQLiteJobRepository(IJobRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, job: Job) -> Job:
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._db.get(Job, job_id)

    def list_by_project(self, project_id: str) -> list[Job]:
        return list(self._db.query(Job).filter(Job.project_id == project_id).order_by(Job.started_at.desc()).all())

    def update(self, job: Job) -> Job:
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return job
