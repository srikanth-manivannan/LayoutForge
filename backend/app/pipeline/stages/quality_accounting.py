"""QualityAccounting stage (Phase 2.7).

Computes the per-stage conservation ledger + release scorecard from the final
tree and stores it on the document (→ idm.json + report.json). Pure
measurement — it never mutates the model — so it is safe to run on every
conversion and gives an objective, comparable definition of "done".
"""

import logging

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.quality.accounting import compute_document_quality
from app.pipeline.quality.fidelity import compute_document_fidelity
from app.pipeline.stages.base import Stage

logger = logging.getLogger("layoutforge.performance")


class QualityAccountingStage(Stage):
    @property
    def name(self) -> str:
        return PipelineStage.QUALITY_ACCOUNTING.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "ReconstructTreeStage must run before QualityAccountingStage"
        quality = compute_document_quality(context.document)
        # M-R1 Document Fidelity Measurement Framework: the full gated score
        # hierarchy (measurement-only; performance family is filled by RVF).
        quality["fidelity"] = compute_document_fidelity(context.document)
        context.document.quality = quality

        low = [s for s in quality["stages"] if s["confidence"] < 1.0]
        logger.info(
            "quality_accounting overall_pass=%s low_confidence_stages=%s",
            quality["overall_pass"],
            [(s["stage"], s["confidence"]) for s in low] or "none",
        )
