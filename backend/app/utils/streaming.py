import uuid
from pathlib import Path

from fastapi import UploadFile

from app.utils.upload_validation import UploadValidationError

_CHUNK_SIZE = 1024 * 1024


async def save_upload_to_temp(file: UploadFile, temp_dir: Path, max_size_bytes: int) -> tuple[Path, int]:
    """Streams an UploadFile to a temp file without loading it fully into
    memory, enforcing the size limit as it goes. Cleans up the partial file
    and raises UploadValidationError if the limit is exceeded."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}.pdf"

    total = 0
    with temp_path.open("wb") as out:
        while chunk := await file.read(_CHUNK_SIZE):
            total += len(chunk)
            if total > max_size_bytes:
                out.close()
                temp_path.unlink(missing_ok=True)
                raise UploadValidationError(
                    f"File exceeds the maximum upload size of {max_size_bytes // (1024 * 1024)} MB."
                )
            out.write(chunk)

    return temp_path, total
