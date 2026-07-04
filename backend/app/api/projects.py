from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import SettingsDep, get_conversion_service, get_project_service
from app.schemas.project import ProjectCreateResponse, ProjectRead
from app.services.conversion_service import ConversionService
from app.services.project_service import ProjectService
from app.utils.streaming import save_upload_to_temp
from app.utils.upload_validation import UploadValidationError

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_project(
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    conversion_service: Annotated[ConversionService, Depends(get_conversion_service)],
    file: UploadFile = File(...),
    name: str | None = Form(None),
) -> ProjectCreateResponse:
    try:
        temp_path, size_bytes = await save_upload_to_temp(file, settings.temp_dir, settings.max_upload_size_bytes)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        project, job = project_service.create_project_from_upload(
            temp_path=temp_path,
            original_filename=file.filename or "upload.pdf",
            size_bytes=size_bytes,
            display_name=name,
        )
    except UploadValidationError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    background_tasks.add_task(conversion_service.run_pipeline, job.id)
    return ProjectCreateResponse(project_id=project.id, job_id=job.id)


@router.get("", response_model=list[ProjectRead])
def list_projects(project_service: Annotated[ProjectService, Depends(get_project_service)]) -> list[ProjectRead]:
    return [ProjectRead.model_validate(p) for p in project_service.list_projects()]


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: str, project_service: Annotated[ProjectService, Depends(get_project_service)]
) -> ProjectRead:
    project = project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, project_service: Annotated[ProjectService, Depends(get_project_service)]) -> None:
    deleted = project_service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
