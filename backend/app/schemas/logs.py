from typing import Literal

from pydantic import BaseModel

LogStream = Literal["application", "conversion", "performance"]


class LogRead(BaseModel):
    stream: LogStream
    lines: list[str]
    truncated: bool
