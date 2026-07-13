"""The Render Instruction Layer (RIL) — the permanent rendering architecture
(docs/RENDER_INSTRUCTION_LAYER.md, approved 2026-07-12).

    Rich IDM (canonical)
       ↓  Instruction Builder   (engine-side: ALL decisions, deterministic)
    Render Tree (derived — built per conversion, validated, then discarded;
       ↓                         never serialized as an editing model)
    Compilers (pure: HTML today; XHTML/EPUB/SVG/PML later — same tree)

Binding rules: compilers import ONLY RenderNode (never Paragraph/Line/Run/
Word/Glyph); the tree is deterministic (same IDM → identical tree — no
runtime decisions, no browser measurements, no thresholds in any compiler);
compilers never repair (rise/baseline/tracking/anchors are already data);
the RenderTreeValidator gates every tree before any compiler runs.
"""

from app.pipeline.rendering.render_tree import RenderNode, build_render_tree
from app.pipeline.rendering.tree_validator import RenderTreeValidationError, validate_render_tree

__all__ = ["RenderNode", "build_render_tree", "RenderTreeValidationError", "validate_render_tree"]
