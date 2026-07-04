import logging
import math
import time
import uuid

import fitz

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.textbox import TextBlock, TextSpan, WordBox
from app.pipeline.stages.base import Stage

logger = logging.getLogger("layoutforge.pipeline")


def _resolve_words(
    line_bbox: tuple,
    spans: list[dict],
    words_by_row: dict[int, list[tuple]],
    baseline_y: float,
    font_id_by_name: dict[str, str],
) -> list[WordBox]:
    """Matches this line's word boxes (from get_text('words')) to their
    style runs. A word inherits the font/size/color of the span whose
    x-range contains the word's midpoint — style changes at word
    boundaries in every case that matters here (a bold word inside a
    sentence, small-caps, etc.). Returns [] if no words fall on the line,
    so the renderer falls back to span rendering."""
    x0, y0, x1, y1 = line_bbox
    cy = (y0 + y1) / 2
    candidates: list[tuple] = []
    for row in (round(cy / 2.0) - 1, round(cy / 2.0), round(cy / 2.0) + 1):
        for word in words_by_row.get(row, []):
            wcy = (word[1] + word[3]) / 2
            if y0 - 1 <= wcy <= y1 + 1 and word[0] >= x0 - 1 and word[2] <= x1 + 1:
                candidates.append(word)
    if not candidates:
        return []
    candidates.sort(key=lambda w: w[0])

    span_ranges = []
    for span in spans:
        sb = span.get("bbox")
        if sb:
            span_ranges.append((sb[0], sb[2], span))

    def style_for(mid_x: float) -> dict:
        for left, right, span in span_ranges:
            if left - 0.5 <= mid_x <= right + 0.5:
                return span
        return spans[0] if spans else {}

    result: list[WordBox] = []
    seen: set[tuple] = set()
    for word in candidates:
        key = (round(word[0], 1), word[4])
        if key in seen:
            continue
        seen.add(key)
        span = style_for((word[0] + word[2]) / 2)
        result.append(
            WordBox(
                text=word[4],
                x=word[0],
                width=word[2] - word[0],
                baseline_y=baseline_y,
                font_id=font_id_by_name.get(span.get("font", "")),
                font_size=span.get("size", 0.0),
                color=f"#{span.get('color', 0):06x}",
            )
        )
    return result


class ExtractTextStage(Stage):
    """Extracts text into normalized TextBlocks, one per PDF "line". Each
    line's PyMuPDF spans become TextBlock.spans (preserving per-run
    color/font — PDFs routinely mix styles mid-line, e.g. a sentence with
    a few differently-colored words), not just the line's first span.
    Reading order and line height are left to NormalizeIdmStage, which
    sees every page at once and can make cross-block decisions extraction
    can't."""

    @property
    def name(self) -> str:
        return PipelineStage.EXTRACT_TEXT.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "MetadataStage must run before ExtractTextStage"
        font_id_by_name: dict[str, str] = context.scratch.get("font_id_by_name", {})

        with fitz.open(context.source_pdf_path) as pdf:
            for index, pdf_page in enumerate(pdf, start=1):
                started = time.perf_counter()
                page = context.document.get_page(index)
                if page is None:
                    continue

                try:
                    raw = pdf_page.get_text("dict")
                except Exception:  # noqa: BLE001 - one bad page must not abort the whole document
                    logger.warning("page=%s extract_text failed", index, exc_info=True)
                    continue

                # Word boxes (typography Milestone 1): exact per-word extents
                # from the same layout pass. Grouped by rounded y so each line
                # can claim its own words in O(1). Cheap even on large pages.
                words_by_row: dict[int, list[tuple]] = {}
                try:
                    for word in pdf_page.get_text("words"):
                        row = round((word[1] + word[3]) / 2 / 2.0)
                        words_by_row.setdefault(row, []).append(word)
                except Exception:  # noqa: BLE001 - words are an enhancement; never abort the page
                    words_by_row = {}

                block_count = 0
                for block in raw.get("blocks", []):
                    if block.get("type") != 0:  # 0 = text, 1 = image (handled by ExtractImagesStage)
                        continue

                    for line in block.get("lines", []):
                        spans = line.get("spans", [])
                        text = "".join(span.get("text", "") for span in spans)
                        if not text.strip():
                            continue

                        primary = spans[0]
                        dx, dy = line.get("dir", (1.0, 0.0))
                        rotation = round(math.degrees(math.atan2(dy, dx)), 2)
                        writing_direction = "rtl" if dx < 0 else "ltr"
                        bbox = line.get("bbox", block.get("bbox", (0, 0, 0, 0)))
                        origin = primary.get("origin", (bbox[0], bbox[3]))

                        text_spans = [
                            TextSpan(
                                text=span.get("text", ""),
                                font_id=font_id_by_name.get(span.get("font", "")),
                                font_size=span.get("size", 0.0),
                                color=f"#{span.get('color', 0):06x}",
                            )
                            for span in spans
                        ]

                        words = _resolve_words(
                            bbox, spans, words_by_row, origin[1], font_id_by_name
                        ) if rotation == 0.0 and writing_direction == "ltr" else []

                        page.text_blocks.append(
                            TextBlock(
                                id=str(uuid.uuid4()),
                                page=index,
                                bbox=BoundingBox(
                                    x=bbox[0], y=bbox[1], width=bbox[2] - bbox[0], height=bbox[3] - bbox[1]
                                ),
                                text=text,
                                font_id=font_id_by_name.get(primary.get("font", "")),
                                font_size=primary.get("size", 0.0),
                                color=f"#{primary.get('color', 0):06x}",
                                rotation=rotation,
                                writing_direction=writing_direction,
                                origin_x=origin[0],
                                origin_y=origin[1],
                                ascender=primary.get("ascender", 0.8),
                                descender=primary.get("descender", -0.2),
                                spans=text_spans,
                                words=words,
                            )
                        )
                        block_count += 1

                logger.info(
                    "page=%s extract_text blocks=%s duration_ms=%.1f",
                    index,
                    block_count,
                    (time.perf_counter() - started) * 1000,
                )
