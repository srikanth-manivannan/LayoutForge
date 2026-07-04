from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_env: str
    storage_ok: bool
