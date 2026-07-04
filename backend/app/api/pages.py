from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_page_repository
from app.repositories.interfaces import IPageRepository
from app.schemas.page import PageRead

router = APIRouter(prefix="/projects/{project_id}/pages", tags=["pages"])


@router.get("", response_model=list[PageRead])
def list_pages(
    project_id: str, page_repository: Annotated[IPageRepository, Depends(get_page_repository)]
) -> list[PageRead]:
    pages = page_repository.list_by_project(project_id)
    return [PageRead.model_validate(p) for p in pages]
