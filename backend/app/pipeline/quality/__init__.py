"""Measured quality (Phase 2.7).

An objective, per-conversion definition of "done": a per-stage conservation
ledger (Expected / Observed / Delta / Confidence) plus a release scorecard
(character fidelity, lexical conservation, font resolution, validator errors).
Measured quality — not visual inspection — is what tells us a conversion is
safe to ship, and where the *first* wrong decision was made when it isn't.
"""

from app.pipeline.quality.accounting import compute_document_quality

__all__ = ["compute_document_quality"]
