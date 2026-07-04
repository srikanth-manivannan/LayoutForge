from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_summary_service
from app.schemas.summary import ProjectSummary
from app.services.summary_service import SummaryService

router = APIRouter(prefix="/projects/{project_id}", tags=["summary"])


@router.get("/summary", response_model=ProjectSummary)
def get_project_summary(
    project_id: str, summary_service: Annotated[SummaryService, Depends(get_summary_service)]
) -> ProjectSummary:
    summary = summary_service.get_summary(project_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return summary
