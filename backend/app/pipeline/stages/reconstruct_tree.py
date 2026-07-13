"""ReconstructTree stage (ADR-011, Phase 2).

Builds the Rich IDM (`page.regions`) in parallel with the frozen legacy
`text_blocks`, running the single-responsibility builder chain:

    Geometry (already normalized) → Run → Line → Paragraph → Region

Then it enforces the strict-pipeline contract (ADR-011): the tree it hands
downstream MUST preserve 100% of the characters extraction produced. The
builders only regroup existing text, so any mismatch is a builder bug and
fails loudly rather than silently emitting a lossy model. Nothing renders the
tree yet (Phase 3), so this stage is purely additive.
"""

import logging
import time
from collections import Counter

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.elements.page import Page
from app.pipeline.stages.base import Stage
from app.pipeline.typography.line_builder import build_line
from app.pipeline.typography.paragraph_builder import build_paragraphs
from app.pipeline.typography.region_builder import build_regions

logger = logging.getLogger("layoutforge.pipeline")


class ReconstructTreeStage(Stage):
    @property
    def name(self) -> str:
        return PipelineStage.RECONSTRUCT_TREE.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "Extraction stages must run before ReconstructTreeStage"
        fonts_by_id = {font.id: font for font in context.document.fonts}

        totals = {"regions": 0, "paragraphs": 0, "runs": 0}
        for page in context.document.pages:
            started = time.perf_counter()
            lines = [
                build_line(block, index, fonts_by_id)
                for index, block in enumerate(page.text_blocks)
            ]
            paragraphs = build_paragraphs(lines, fonts_by_id)
            page.regions = build_regions(paragraphs)

            self._assert_character_fidelity(page)

            runs = sum(len(line.runs) for p in paragraphs for line in p.lines)
            totals["regions"] += len(page.regions)
            totals["paragraphs"] += len(paragraphs)
            totals["runs"] += runs
            logger.info(
                "page=%s reconstruct_tree regions=%s paragraphs=%s lines=%s runs=%s duration_ms=%.1f",
                page.number,
                len(page.regions),
                len(paragraphs),
                len(lines),
                runs,
                (time.perf_counter() - started) * 1000,
            )

        logger.info(
            "reconstruct_tree total regions=%s paragraphs=%s runs=%s",
            totals["regions"],
            totals["paragraphs"],
            totals["runs"],
        )

    @staticmethod
    def _assert_character_fidelity(page: Page) -> None:
        """Gate 0 (LFS §2, ADR-010) at the model→model boundary: the tree must
        carry every character the legacy lines carried. Compared as a
        character multiset so contiguous regrouping order is irrelevant."""
        legacy = Counter("".join(block.text for block in page.text_blocks))
        tree = Counter(
            "".join(
                run.text
                for region in page.regions
                for paragraph in region.paragraphs
                for line in paragraph.lines
                for run in line.runs
            )
        )
        lost = legacy - tree
        if lost:
            raise ValueError(
                f"reconstruct_tree lost characters on page {page.number}: "
                f"{dict(list(lost.items())[:10])}"
            )
