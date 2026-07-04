import os
import tempfile
from pathlib import Path

# Must run before any `app.*` module is imported by a test file, so the app
# (and its module-level `app = create_app()`) is built against an isolated
# storage root/database rather than the developer's real storage/ directory.
_TEST_STORAGE = Path(tempfile.mkdtemp(prefix="layoutforge_test_"))
os.environ["STORAGE_ROOT"] = str(_TEST_STORAGE)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_STORAGE / 'test.db').as_posix()}"

import fitz  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database.base import Base  # noqa: E402
from app import models  # noqa: E402,F401


@pytest.fixture
def db_session():
    """An isolated, in-memory database session for repository/service unit
    tests that don't need the full FastAPI app."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_pdf_bytes(pages: int = 1) -> bytes:
    document = fitz.open()
    for _ in range(pages):
        document.new_page(width=200, height=300)
    data = document.tobytes()
    document.close()
    return data


def make_encrypted_pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page(width=200, height=300)
    data = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()
    return data


def _solid_png_bytes(color: tuple[int, int, int] = (200, 30, 30), size: tuple[int, int] = (40, 40)) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_rich_pdf_bytes(pages: int = 2, with_image: bool = True, rotation: int = 0) -> bytes:
    """A PDF with real text (in a bold and a non-bold font, to exercise font
    extraction) and an embedded image, for extraction-stage tests."""
    document = fitz.open()
    image_bytes = _solid_png_bytes() if with_image else None
    for page_index in range(pages):
        page = document.new_page(width=300, height=400)
        if rotation:
            page.set_rotation(rotation)
        page.insert_text((50, 80), f"Page {page_index + 1} heading", fontsize=18, fontname="hebo")
        page.insert_text((50, 120), "Body copy line one.", fontsize=10, fontname="helv")
        if image_bytes:
            page.insert_image(fitz.Rect(50, 200, 150, 260), stream=image_bytes)
    data = document.tobytes()
    document.close()
    return data


def make_multicolor_line_pdf_bytes() -> bytes:
    """One page with a single PDF line made of three differently-colored
    runs in sequence (same baseline, same font) — reproducing the
    real-world case found in production PDFs: PyMuPDF groups these into
    one "line" with multiple "spans", each carrying its own color."""
    document = fitz.open()
    page = document.new_page(width=400, height=200)
    y = 80
    page.insert_text((50, y), "Blue ", fontsize=14, fontname="helv", color=(0, 0, 1))
    x2 = 50 + fitz.get_text_length("Blue ", fontname="helv", fontsize=14)
    page.insert_text((x2, y), "Black ", fontsize=14, fontname="helv", color=(0, 0, 0))
    x3 = 50 + fitz.get_text_length("Blue Black ", fontname="helv", fontsize=14)
    page.insert_text((x3, y), "Orange", fontsize=14, fontname="helv", color=(1, 0.5, 0))
    data = document.tobytes()
    document.close()
    return data


def make_empty_page_pdf_bytes(pages: int = 1) -> bytes:
    """Pages with geometry but no text/images/fonts at all."""
    return make_pdf_bytes(pages=pages)


def make_minimal_ttf_bytes() -> bytes:
    """A tiny but structurally complete, valid TrueType font, built
    in-memory so font-sanitization tests don't depend on any external
    font file (which would make them platform-specific)."""
    import io

    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 500))
    pen.lineTo((500, 500))
    pen.lineTo((500, 0))
    pen.closePath()
    glyph = pen.glyph()

    builder = FontBuilder(unitsPerEm=1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "A"])
    builder.setupCharacterMap({65: "A"})
    builder.setupGlyf({".notdef": glyph, "A": glyph})
    builder.setupHorizontalMetrics({".notdef": (500, 0), "A": (500, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()

    buffer = io.BytesIO()
    builder.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return make_pdf_bytes(pages=3)


@pytest.fixture
def encrypted_pdf_bytes() -> bytes:
    return make_encrypted_pdf_bytes()


@pytest.fixture
def rich_pdf_path(tmp_path) -> Path:
    path = tmp_path / "rich.pdf"
    path.write_bytes(make_rich_pdf_bytes(pages=2))
    return path
