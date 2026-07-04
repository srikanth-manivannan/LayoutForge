from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.interfaces import IProjectRepository


class SQLiteProjectRepository(IProjectRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, project: Project) -> Project:
        self._db.add(project)
        self._db.commit()
        self._db.refresh(project)
        return project

    def get(self, project_id: str) -> Project | None:
        return self._db.get(Project, project_id)

    def list(self) -> list[Project]:
        return list(self._db.query(Project).order_by(Project.created_at.desc()).all())

    def update(self, project: Project) -> Project:
        self._db.add(project)
        self._db.commit()
        self._db.refresh(project)
        return project

    def delete(self, project_id: str) -> None:
        project = self.get(project_id)
        if project is not None:
            self._db.delete(project)
            self._db.commit()
