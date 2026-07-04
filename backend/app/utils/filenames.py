import re
import unicodedata

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(original: str) -> str:
    """Strips path components and unsafe characters from a user-supplied
    filename, preventing path traversal (../, absolute paths, separators)
    while preserving the original name for display purposes."""
    name = original.replace("\\", "/").rsplit("/", 1)[-1]
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = _UNSAFE_CHARS.sub("_", name).strip("._")
    return name or "upload.pdf"
