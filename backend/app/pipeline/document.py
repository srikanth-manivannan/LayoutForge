from dataclasses import dataclass, field

from app.pipeline.elements.asset import AssetResource
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page


@dataclass
class DocumentMetadata:
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modification_date: str | None = None
    page_count: int = 0

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentMetadata":
        return cls(**data)


@dataclass
class Document:
    """The Internal Document Model (IDM) — the single source of truth
    between input adapters (e.g. the PyMuPDF extractor) and output plugins
    (HTML, CSS, manifest, and future EPUB/JSON/XML). Output plugins must
    only read from this model and must never depend on the originating PDF
    library. `to_dict`/`from_dict` let this model be persisted to and
    rebuilt from disk (see StorageService.save_idm/load_idm) so later
    pipeline stages or output plugins never need to reopen the source PDF."""

    project_id: str
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    pages: list[Page] = field(default_factory=list)
    fonts: list[FontResource] = field(default_factory=list)
    assets: list[AssetResource] = field(default_factory=list)
    # Adaptive Reconstruction analytics (M1.6): counts by mode/reason +
    # mean confidence across the document. Diagnostic, not user-facing —
    # feeds engine tuning and Validation. Empty until reconstruction runs.
    reconstruction_profile: dict = field(default_factory=dict)

    def get_page(self, number: int) -> Page | None:
        for page in self.pages:
            if page.number == number:
                return page
        return None

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "metadata": self.metadata.to_dict(),
            "pages": [p.to_dict() for p in self.pages],
            "fonts": [f.to_dict() for f in self.fonts],
            "assets": [a.to_dict() for a in self.assets],
            "reconstruction_profile": self.reconstruction_profile,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        return cls(
            project_id=data["project_id"],
            metadata=DocumentMetadata.from_dict(data["metadata"]),
            pages=[Page.from_dict(p) for p in data.get("pages", [])],
            fonts=[FontResource.from_dict(f) for f in data.get("fonts", [])],
            assets=[AssetResource.from_dict(a) for a in data.get("assets", [])],
            reconstruction_profile=data.get("reconstruction_profile", {}),
        )
