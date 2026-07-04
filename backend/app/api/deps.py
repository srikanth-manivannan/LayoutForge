from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.settings import get_settings
from app.database.session import get_db
from app.events.dispatcher import dispatcher
from app.repositories.interfaces import IAssetRepository, IJobRepository, IPageRepository, IProjectRepository
from app.repositories.sqlite import (
    SQLiteAssetRepository,
    SQLiteJobRepository,
    SQLitePageRepository,
    SQLiteProjectRepository,
)
from app.services.conversion_service import ConversionService
from app.services.logs_service import LogsService
from app.services.project_service import ProjectService
from app.services.storage_service import StorageService
from app.services.summary_service import SummaryService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]


def get_storage_service(settings: SettingsDep) -> StorageService:
    return StorageService(settings)


def get_project_repository(db: DbDep) -> IProjectRepository:
    return SQLiteProjectRepository(db)


def get_job_repository(db: DbDep) -> IJobRepository:
    return SQLiteJobRepository(db)


def get_page_repository(db: DbDep) -> IPageRepository:
    return SQLitePageRepository(db)


def get_asset_repository(db: DbDep) -> IAssetRepository:
    return SQLiteAssetRepository(db)


def get_project_service(
    project_repository: Annotated[IProjectRepository, Depends(get_project_repository)],
    job_repository: Annotated[IJobRepository, Depends(get_job_repository)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    settings: SettingsDep,
) -> ProjectService:
    return ProjectService(project_repository, job_repository, storage_service, settings, dispatcher)


def get_conversion_service(
    job_repository: Annotated[IJobRepository, Depends(get_job_repository)],
    project_repository: Annotated[IProjectRepository, Depends(get_project_repository)],
    page_repository: Annotated[IPageRepository, Depends(get_page_repository)],
    asset_repository: Annotated[IAssetRepository, Depends(get_asset_repository)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
    settings: SettingsDep,
) -> ConversionService:
    return ConversionService(
        job_repository, project_repository, page_repository, asset_repository, storage_service, settings, dispatcher
    )


def get_summary_service(
    project_repository: Annotated[IProjectRepository, Depends(get_project_repository)],
    job_repository: Annotated[IJobRepository, Depends(get_job_repository)],
    page_repository: Annotated[IPageRepository, Depends(get_page_repository)],
    asset_repository: Annotated[IAssetRepository, Depends(get_asset_repository)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> SummaryService:
    return SummaryService(project_repository, job_repository, page_repository, asset_repository, storage_service)


def get_logs_service(storage_service: Annotated[StorageService, Depends(get_storage_service)]) -> LogsService:
    return LogsService(storage_service)
