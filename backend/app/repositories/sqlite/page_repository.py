from sqlalchemy.orm import Session

from app.models.page import Page
from app.repositories.interfaces import IPageRepository


class SQLitePageRepository(IPageRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, page: Page) -> Page:
        self._db.add(page)
        self._db.commit()
        self._db.refresh(page)
        return page

    def bulk_create(self, pages: list[Page]) -> list[Page]:
        self._db.add_all(pages)
        self._db.commit()
        for page in pages:
            self._db.refresh(page)
        return pages

    def list_by_project(self, project_id: str) -> list[Page]:
        return list(
            self._db.query(Page).filter(Page.project_id == project_id).order_by(Page.page_number.asc()).all()
        )

    def update(self, page: Page) -> Page:
        self._db.add(page)
        self._db.commit()
        self._db.refresh(page)
        return page
