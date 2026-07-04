from app.core.enums import JobStatus, ProjectStatus
from app.models.job import Job
from app.models.project import Project
from app.repositories.sqlite.job_repository import SQLiteJobRepository
from app.repositories.sqlite.project_repository import SQLiteProjectRepository


def test_project_repository_create_get_update_delete(db_session) -> None:
    repo = SQLiteProjectRepository(db_session)

    project = repo.create(Project(name="Report", filename="report.pdf", page_count=2))
    assert project.id
    assert project.status == ProjectStatus.CREATED

    fetched = repo.get(project.id)
    assert fetched is not None
    assert fetched.name == "Report"

    fetched.status = ProjectStatus.READY
    updated = repo.update(fetched)
    assert updated.status == ProjectStatus.READY

    assert [p.id for p in repo.list()] == [project.id]

    repo.delete(project.id)
    assert repo.get(project.id) is None


def test_job_repository_create_and_update(db_session) -> None:
    project_repo = SQLiteProjectRepository(db_session)
    job_repo = SQLiteJobRepository(db_session)

    project = project_repo.create(Project(name="Report", filename="report.pdf", page_count=1))
    job = job_repo.create(Job(project_id=project.id))

    assert job.status == JobStatus.QUEUED
    assert job_repo.list_by_project(project.id) == [job]

    job.status = JobStatus.RUNNING
    job.progress = 50
    updated = job_repo.update(job)
    assert updated.status == JobStatus.RUNNING
    assert updated.progress == 50
