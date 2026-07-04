from pathlib import Path

import fitz

PDF_MAGIC = b"%PDF-"


class UploadValidationError(Exception):
    """A user-facing validation failure; the message is safe to return in an API error response."""


def validate_extension(filename: str, allowed_extensions: list[str]) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(allowed_extensions)
        raise UploadValidationError(f"Unsupported file type '{suffix}'. Allowed: {allowed}")


def validate_mime(file_path: Path) -> None:
    with file_path.open("rb") as f:
        header = f.read(len(PDF_MAGIC))
    if header != PDF_MAGIC:
        raise UploadValidationError("The uploaded file is not a valid PDF (missing PDF signature).")


def validate_pdf_structure(file_path: Path) -> fitz.Document:
    """Opens the PDF to confirm it parses and is not password-protected.
    Returns the open Document so callers can reuse it (e.g. for page_count)
    without re-parsing; the caller is responsible for closing it."""
    try:
        document = fitz.open(file_path)
    except Exception as exc:  # noqa: BLE001 - any parse failure is a validation failure
        raise UploadValidationError("The uploaded file is not a valid or readable PDF.") from exc

    if document.needs_pass:
        document.close()
        raise UploadValidationError("Password-protected PDFs are not supported.")

    return document
