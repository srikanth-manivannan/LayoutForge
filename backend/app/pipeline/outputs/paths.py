def resource_href(project_relative_path: str) -> str:
    """Relative URL for a project asset, as referenced from a generated
    HTML page (which lives in the project's pages/ directory). Going up one
    level reaches the project root, where resources/ lives.

    Relative (not absolute) URLs make each project workspace fully
    self-contained: the same page_XXXX.html renders identically whether
    opened directly from disk (file://), served by the backend, or loaded
    into an iframe — no per-renderer URL rewriting anywhere."""
    return f"../{project_relative_path}"
