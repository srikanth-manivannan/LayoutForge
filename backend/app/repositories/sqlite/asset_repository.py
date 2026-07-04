from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_page_link import AssetPageLink
from app.repositories.interfaces import IAssetRepository


class SQLiteAssetRepository(IAssetRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, asset: Asset) -> Asset:
        self._db.add(asset)
        self._db.commit()
        self._db.refresh(asset)
        return asset

    def get_by_hash(self, project_id: str, content_hash: str) -> Asset | None:
        return (
            self._db.query(Asset)
            .filter(Asset.project_id == project_id, Asset.hash == content_hash)
            .one_or_none()
        )

    def list_by_project(self, project_id: str) -> list[Asset]:
        return list(self._db.query(Asset).filter(Asset.project_id == project_id).all())

    def add_page_reference(self, asset_id: str, page_number: int) -> None:
        exists = (
            self._db.query(AssetPageLink)
            .filter(AssetPageLink.asset_id == asset_id, AssetPageLink.page_number == page_number)
            .one_or_none()
        )
        if exists is None:
            self._db.add(AssetPageLink(asset_id=asset_id, page_number=page_number))
            self._db.commit()

    def list_pages_for_asset(self, asset_id: str) -> list[int]:
        rows = self._db.query(AssetPageLink).filter(AssetPageLink.asset_id == asset_id).all()
        return sorted({row.page_number for row in rows})
