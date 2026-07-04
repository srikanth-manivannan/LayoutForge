from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_logs_service
from app.schemas.logs import LogRead, LogStream
from app.services.logs_service import LogsService

router = APIRouter(prefix="/logs", tags=["logs"])

_DEFAULT_TAIL = 200


@router.get("", response_model=LogRead)
def get_logs(
    logs_service: Annotated[LogsService, Depends(get_logs_service)],
    stream: LogStream = Query("application"),
    tail: int = Query(_DEFAULT_TAIL, ge=1, le=2000),
) -> LogRead:
    # `stream` is a Literal["application","conversion","performance"] — FastAPI
    # rejects any other value with a 422 before this body runs, so only a
    # fixed, known filename is ever read (never an arbitrary path).
    lines, truncated = logs_service.tail(stream, tail)
    return LogRead(stream=stream, lines=lines, truncated=truncated)
