from app import models  # noqa: F401 - ensures all model classes are registered on Base.metadata
from app.database.base import Base
from app.database.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
