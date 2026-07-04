from app.schemas.logs import LogStream
from app.services.storage_service import StorageService

_LOG_FILENAMES: dict[LogStream, str] = {
    "application": "application.log",
    "conversion": "conversion.log",
    "performance": "performance.log",
}

_DEFAULT_TAIL = 200
_MAX_TAIL = 2000


class LogsService:
    """Tails one of the three fixed, rotating log files written by
    `utils/logging_config.py`. Only ever reads a name from a fixed
    allow-list (`_LOG_FILENAMES`) joined onto `StorageService.logs_dir` —
    never an arbitrary, caller-supplied path."""

    def __init__(self, storage_service: StorageService) -> None:
        self._storage = storage_service

    def tail(self, stream: LogStream, tail: int) -> tuple[list[str], bool]:
        tail = max(1, min(tail, _MAX_TAIL))
        log_path = self._storage.logs_dir / _LOG_FILENAMES[stream]
        if not log_path.is_file():
            return [], False

        try:
            all_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return [], False

        truncated = len(all_lines) > tail
        return all_lines[-tail:], truncated
