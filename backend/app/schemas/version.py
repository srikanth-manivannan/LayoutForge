from pydantic import BaseModel


class VersionInfo(BaseModel):
    version: str
    build: str
    git_commit: str | None
    api_version: int
