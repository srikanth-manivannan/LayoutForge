"""Writers (ADR-011, Phase 3).

The renderer is a **compiler** from the Rich IDM to an output format — never a
repair stage. A generic RenderEngine dispatches to a target-specific Writer
(HTML today; Fixed-Layout, EPUB, XML, PML reserved), each consuming the same
`Document` through a `WriterContext` (target + feature flags + LFS version +
edition). A writer never knows another format exists.
"""

from app.pipeline.outputs.writers.context import FeatureFlags, Target, WriterContext
from app.pipeline.outputs.writers.render_engine import RenderEngine, UnsupportedTargetError
from app.pipeline.outputs.writers.style_registry import StyleRegistry

__all__ = [
    "FeatureFlags",
    "Target",
    "WriterContext",
    "RenderEngine",
    "UnsupportedTargetError",
    "StyleRegistry",
]
