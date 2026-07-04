from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.pipeline.document import Document


@dataclass
class PipelineContext:
    """Mutable state threaded through every pipeline stage for a single job."""

    job_id: str
    project_id: str
    source_pdf_path: Path
    output_dir: Path
    document: Document | None = None
    scratch: dict[str, Any] = field(default_factory=dict)
