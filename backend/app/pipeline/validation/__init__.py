"""Rich IDM validation (Phase 2.5, ADR-011).

The model must prove internally correct before any renderer consumes it — a
renderer is a compiler over a *valid* tree, never a place to compensate for
model inconsistencies. The validator walks the Rich IDM and reports structural
and fidelity violations (empty/foreign-referencing runs, words crossing run
boundaries, lines/paragraphs missing children, baseline inversions, character
loss, duplicate ids). Goal: every page passes 100% before HTML generation.
"""

from app.pipeline.validation.idm_validator import Violation, validate_document

__all__ = ["Violation", "validate_document"]
