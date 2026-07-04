from pathlib import Path

import pytest

from app.utils.upload_validation import (
    UploadValidationError,
    validate_extension,
    validate_mime,
    validate_pdf_structure,
)
from tests.conftest import make_encrypted_pdf_bytes, make_pdf_bytes


def test_validate_extension_accepts_pdf() -> None:
    validate_extension("report.PDF", [".pdf"])


def test_validate_extension_rejects_other_types() -> None:
    with pytest.raises(UploadValidationError):
        validate_extension("report.docx", [".pdf"])


def test_validate_mime_accepts_pdf_signature(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf_bytes())
    validate_mime(path)


def test_validate_mime_rejects_non_pdf_bytes(tmp_path: Path) -> None:
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"not a pdf at all")
    with pytest.raises(UploadValidationError):
        validate_mime(path)


def test_validate_pdf_structure_accepts_valid_pdf(tmp_path: Path) -> None:
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf_bytes(pages=2))
    document = validate_pdf_structure(path)
    try:
        assert document.page_count == 2
    finally:
        document.close()


def test_validate_pdf_structure_rejects_password_protected(tmp_path: Path) -> None:
    path = tmp_path / "encrypted.pdf"
    path.write_bytes(make_encrypted_pdf_bytes())
    with pytest.raises(UploadValidationError):
        validate_pdf_structure(path)


def test_validate_pdf_structure_rejects_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.4\nthis is not really a pdf body")
    with pytest.raises(UploadValidationError):
        validate_pdf_structure(path)
