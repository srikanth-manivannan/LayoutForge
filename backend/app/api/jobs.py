from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_job_repository
from app.repositories.interfaces import IJobRepository
from app.schemas.job import JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, job_repository: Annotated[IJobRepository, Depends(get_job_repository)]) -> JobRead:
    job = job_repository.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job)
