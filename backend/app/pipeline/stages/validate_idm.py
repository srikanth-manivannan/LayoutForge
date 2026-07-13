"""ValidateRichIdm stage (Phase 2.5).

Runs the Rich IDM validator after the tree is built and records the summary on
the document (persisted to idm.json + report.json). Policy: **advisory by
default** — it surfaces and counts violations without failing the conversion,
because the legacy writer (the current runtime default) does not consume the
tree and must keep working while the model is brought to 100% validity.

When `strict=True` (paired with semantic rendering), an error-severity
violation raises: the semantic renderer refuses to consume an invalid model.
That is the gate the project drives toward — validator green on the whole
corpus, *then* the semantic writer becomes the default.
"""

import logging

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import Stage
from app.pipeline.validation.idm_validator import summarize, validate_document

logger = logging.getLogger("layoutforge.pipeline")


class RichIdmValidationError(Exception):
    """Raised in strict mode when the tree has error-severity violations."""


class ValidateRichIdmStage(Stage):
    def __init__(self, *, strict: bool = False) -> None:
        self._strict = strict

    @property
    def name(self) -> str:
        return PipelineStage.VALIDATE_IDM.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "ReconstructTreeStage must run before ValidateRichIdmStage"

        violations = validate_document(context.document)
        summary = summarize(violations)
        context.document.idm_validation = summary

        if summary["errors"] or summary["warnings"]:
            logger.warning(
                "validate_idm errors=%s warnings=%s by_code=%s",
                summary["errors"], summary["warnings"], summary["by_code"],
            )
        else:
            logger.info("validate_idm clean: 0 violations")

        if self._strict and summary["errors"]:
            raise RichIdmValidationError(
                f"Rich IDM has {summary['errors']} error(s): {summary['by_code']}"
            )
