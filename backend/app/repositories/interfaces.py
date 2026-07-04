from abc import ABC, abstractmethod

from app.models.asset import Asset
from app.models.job import Job
from app.models.page import Page
from app.models.project import Project


class IProjectRepository(ABC):
    @abstractmethod
    def create(self, project: Project) -> Project: ...

    @abstractmethod
    def get(self, project_id: str) -> Project | None: ...

    @abstractmethod
    def list(self) -> list[Project]: ...

    @abstractmethod
    def update(self, project: Project) -> Project: ...

    @abstractmethod
    def delete(self, project_id: str) -> None: ...


class IJobRepository(ABC):
    @abstractmethod
    def create(self, job: Job) -> Job: ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[Job]: ...

    @abstractmethod
    def update(self, job: Job) -> Job: ...


class IPageRepository(ABC):
    @abstractmethod
    def create(self, page: Page) -> Page: ...

    @abstractmethod
    def bulk_create(self, pages: list[Page]) -> list[Page]: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[Page]: ...

    @abstractmethod
    def update(self, page: Page) -> Page: ...


class IAssetRepository(ABC):
    @abstractmethod
    def create(self, asset: Asset) -> Asset: ...

    @abstractmethod
    def get_by_hash(self, project_id: str, content_hash: str) -> Asset | None: ...

    @abstractmethod
    def list_by_project(self, project_id: str) -> list[Asset]: ...

    @abstractmethod
    def add_page_reference(self, asset_id: str, page_number: int) -> None: ...

    @abstractmethod
    def list_pages_for_asset(self, asset_id: str) -> list[int]: ...
