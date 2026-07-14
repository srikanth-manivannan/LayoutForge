import copy
import io
import logging
import re
import time
import uuid
from collections import Counter
from pathlib import Path

import fitz
from fontTools import agl
from fontTools.cffLib import CFFFontSet
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont

from app.core.enums import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.elements.font import FontResource
from app.pipeline.stages.base import Stage
from app.services.storage_service import StorageService

logger = logging.getLogger("layoutforge.pipeline")

_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
_PS_NAME_SAFE = re.compile(r"[^A-Za-z0-9-]")

# Ordered: compound tokens ("semibold", "extrabold") must match before the
# bare "bold"/"light" substrings they contain. Values are the tokens
# font_naming.CSS_WEIGHT_BY_TOKEN maps to CSS weights.
_WEIGHT_TOKENS: list[tuple[str, str]] = [
    ("extrabold", "extrabold"),
    ("ultrabold", "extrabold"),
    ("semibold", "semibold"),
    ("demibold", "semibold"),
    ("demi", "semibold"),
    ("extralight", "extralight"),
    ("ultralight", "extralight"),
    ("hairline", "thin"),
    ("thin", "thin"),
    ("light", "light"),
    ("medium", "medium"),
    ("heavy", "black"),
    ("black", "black"),
    ("bold", "bold"),
]


def _weight_from_name(lowered_family: str) -> str:
    for token, weight in _WEIGHT_TOKENS:
        if token in lowered_family:
            return weight
    return "normal"

# Browsers run every @font-face font through strict sanitization (OTS).
# PDF-embedded font subsets are frequently structurally valid enough for a
# PDF renderer but fail that sanitization (bad checksums, non-conforming
# directory entries) — confirmed in practice: a font with status "error"
# in the browser's FontFaceSet started loading correctly only after being
# re-saved through fontTools, which recomputes checksums and normalizes
# the table directory.
#
# Bare "cff" (a PDF Type1C font program — the payload of an OTF's 'CFF '
# table, not a standalone font file) is not web-loadable as-is, but IS
# recoverable: _wrap_bare_cff rebuilds it into a complete OpenType file.
# Dropping these fonts (the pre-fix behavior) made every text block using
# them render in a fallback font with different metrics — visibly doubled
# against the rasterized background (first seen on the reference book's
# page 26 title, a CFF-embedded HelveticaRounded-Bold).
_WEB_FONT_EXTENSIONS = {"ttf", "otf"}


def _extract_font_buffer(pdf: fitz.Document, xref: int) -> tuple[str, bytes]:
    """Normalizes PyMuPDF's extract_font return shape across versions
    (tuple-of-4 vs dict) into (extension, content_bytes)."""
    result = pdf.extract_font(xref)
    if isinstance(result, dict):
        return result.get("ext", ""), result.get("content", b"") or b""
    _basefont, ext, _subtype, content = result
    return ext or "", content or b""


def _wrap_bare_cff(content: bytes, family: str) -> bytes | None:
    """Rebuilds a bare CFF font program (PDF Type1C) into a complete,
    browser-loadable OpenType file.

    A bare CFF carries outlines, charset, and advance widths but none of
    the sfnt tables (head/hhea/hmtx/cmap/name/OS-2/post) browsers require.
    We recover everything from the CFF itself: widths and bounds by drawing
    each charstring, the character map from the AGL glyph names PDF subsets
    use, and re-emit each outline through T2CharStringPen (which flattens
    subroutines, so the rebuilt CFF is self-contained). Returns None if the
    program can't be parsed — same contract as _sanitize_for_web."""
    try:
        cff = CFFFontSet()
        cff.decompile(io.BytesIO(content), None)
        top = cff[0]
        glyph_order = top.getGlyphOrder()
        charstrings = top.CharStrings

        units_per_em = 1000
        font_matrix = getattr(top, "FontMatrix", None)
        if font_matrix and font_matrix[0]:
            units_per_em = int(round(1 / font_matrix[0]))

        # Pass 1: advance widths + vertical bounds (drawing populates
        # each charstring's .width).
        metrics: dict[str, tuple[int, int]] = {}
        ymin, ymax = 0, 0
        for name in glyph_order:
            charstring = charstrings[name]
            bounds_pen = BoundsPen(charstrings)
            charstring.draw(bounds_pen)
            width = int(round(getattr(charstring, "width", units_per_em) or 0))
            left_side_bearing = int(round(bounds_pen.bounds[0])) if bounds_pen.bounds else 0
            metrics[name] = (width, left_side_bearing)
            if bounds_pen.bounds:
                ymin = min(ymin, bounds_pen.bounds[1])
                ymax = max(ymax, bounds_pen.bounds[3])

        # Pass 2: self-contained charstrings (subroutines flattened).
        rebuilt = {}
        for name in glyph_order:
            pen = T2CharStringPen(metrics[name][0], charstrings)
            charstrings[name].draw(pen)
            rebuilt[name] = pen.getCharString()

        # Character map from AGL glyph names ("exclam", "Y", "uni0041", …).
        cmap: dict[int, str] = {}
        for name in glyph_order:
            if name == ".notdef":
                continue
            unicode_text = agl.toUnicode(name)
            if len(unicode_text) == 1 and ord(unicode_text) not in cmap:
                cmap[ord(unicode_text)] = name

        ps_name = _PS_NAME_SAFE.sub("-", cff.fontNames[0] if cff.fontNames else family)[:63] or "WrappedCFF"

        # Line metrics MUST come from the font's real ascender/descender —
        # not glyph bounds. NormalizeIdmStage computes each block's
        # line_height from PyMuPDF's span ascender/descender, and the
        # browser reconstructs the baseline from the font file's metrics:
        # they only land on the same y when both use the same numbers. A
        # subset's glyph bounds are usually far below the font's ascender
        # (this bug: bounds said 737 where the font says 963 → every glyph
        # painted ~4.6pt above the rasterized background at 42pt). MuPDF
        # parses the same bare-CFF buffer extraction used, so its
        # ascender/descender are exactly the values the IDM recorded.
        ascent = int(round(ymax))
        descent = int(round(ymin))
        try:
            mupdf_font = fitz.Font(fontbuffer=content)
            ascent = int(round(mupdf_font.ascender * units_per_em))
            descent = int(round(mupdf_font.descender * units_per_em))
        except Exception:  # noqa: BLE001 - fall back to glyph bounds if MuPDF can't load the buffer
            logger.warning("MuPDF metrics unavailable for %s; using glyph bounds", family, exc_info=True)

        builder = FontBuilder(units_per_em, isTTF=False)
        builder.setupGlyphOrder(list(glyph_order))
        builder.setupCharacterMap(cmap)
        builder.setupCFF(ps_name, {}, rebuilt, {})
        builder.setupHorizontalMetrics(metrics)
        # All three metric pairs (hhea, sTypo*, usWin*) get the same values:
        # different platforms/browsers pick different pairs for the line box
        # (Chrome on Windows uses usWin*), and any disagreement re-opens the
        # baseline drift this function exists to prevent.
        builder.setupHorizontalHeader(ascent=ascent, descent=descent)
        builder.setupNameTable({"familyName": family, "styleName": "Regular", "psName": ps_name})
        builder.setupOS2(
            sTypoAscender=ascent,
            sTypoDescender=descent,
            usWinAscent=max(ascent, 0),
            usWinDescent=abs(min(descent, 0)),
        )
        builder.setupPost()

        buffer = io.BytesIO()
        builder.save(buffer)
        return buffer.getvalue()
    except Exception:  # noqa: BLE001 - an unparseable font program can't be recovered
        logger.warning("bare-CFF wrapping failed for family=%s, skipping web font", family, exc_info=True)
        return None


def _ensure_required_tables(font: TTFont, family: str) -> None:
    """Synthesizes the sfnt tables browsers REQUIRE but PDF subsets often
    omit (PDF renderers don't need them). OTS rejects the whole file over a
    missing table — confirmed live: PrinceXML subsets shipping without
    OS/2 made every @font-face report status "error", silently dropping
    the entire page to fallback fonts. OS/2 metrics are taken from the
    existing hhea so all metric pairs agree (the baseline-consistency rule
    from the bare-CFF work)."""
    # A subset missing BOTH post and cmap has no source for glyph names —
    # fontTools raises "illegal use of getGlyphOrder()" inside any
    # FontBuilder setup call. (Regression caught live: the sanitizer
    # swallowed that error and silently DROPPED the one ComicSans subset
    # carrying the real c/g/W/quote outlines — invisible characters. The
    # character-fidelity gate now exists so this class of failure can never
    # be silent again.) Synthesize a glyph order up front.
    try:
        font.getGlyphOrder()
    except Exception:  # noqa: BLE001 - no post/cmap to derive names from
        count = font["maxp"].numGlyphs if "maxp" in font else 0
        font.setGlyphOrder([".notdef"] + [f"glyph{i:05d}" for i in range(1, count)])

    builder = FontBuilder(font=font)
    if "name" not in font:
        builder.setupNameTable({"familyName": family, "styleName": "Regular"})
    if "OS/2" not in font:
        ascent = font["hhea"].ascent if "hhea" in font else 800
        descent = font["hhea"].descent if "hhea" in font else -200
        builder.setupOS2(
            sTypoAscender=ascent,
            sTypoDescender=descent,
            usWinAscent=max(ascent, 0),
            usWinDescent=abs(min(descent, 0)),
        )
    if "post" not in font:
        builder.setupPost()
    if "cmap" not in font:
        # Presence is required for OTS, and fontTools can't build an EMPTY
        # cmap — seed one harmless mapping; the texttrace reconciliation /
        # sibling-merge passes fill in the real entries immediately after.
        order = font.getGlyphOrder()
        builder.setupCharacterMap({0x20: order[0]})


def _sanitize_for_web(ext: str, content: bytes, family: str = "LayoutForge") -> bytes | None:
    """Returns browser-loadable font bytes, or None if this font can't be
    served as a web font at all (wrong format) or sanitization failed.
    Re-saving through fontTools normalizes checksums/table directories;
    _ensure_required_tables fills in tables subsets commonly omit."""
    if ext not in _WEB_FONT_EXTENSIONS:
        return None
    try:
        font = TTFont(io.BytesIO(content))
        _ensure_required_tables(font, family)
        buffer = io.BytesIO()
        font.save(buffer)
        return buffer.getvalue()
    except Exception:  # noqa: BLE001 - a font fontTools can't parse can't be sanitized
        logger.warning("font sanitization failed for ext=%s, skipping web font", ext, exc_info=True)
        return None


def _reconcile_cmap_from_usage(fonts_dir: Path, font: FontResource, usage: dict[int, Counter]) -> None:
    """Rewrites a font file's cmap so every (unicode → glyph id) pair the
    PDF ACTUALLY RENDERED (from page.get_texttrace()) maps correctly.

    Many generators (PrinceXML, TeX, InDesign subsets) re-encode embedded
    fonts: the file's internal cmap — if present at all — maps arbitrary
    codes, not the document's Unicode text, because the PDF supplies its
    own encoding on top. Browsers only have the file's cmap, so overlay
    text picks wrong or missing glyphs (garbled/doubled rendering). The
    texttrace is ground truth: the PDF renderer resolved each character to
    a concrete glyph id, so we rebuild the cmap from exactly that.

    A codepoint can legitimately resolve to MORE THAN ONE glyph id across a
    document — e.g. a deliberate InDesign stylistic-alternate substitution
    on only some occurrences of a letter, to avoid visual repetition (Issue
    005, 2026-07-14: found on a real book where 's' rendered via both its
    standard glyph and a '.salt' alternate within one word). A cmap can
    only hold one glyph per codepoint, so `usage[codepoint]` is a Counter
    of every glyph id actually seen, and the MAJORITY glyph is kept — never
    whichever occurrence happened to be processed last."""
    try:
        path = fonts_dir / font.filename
        tt = TTFont(io.BytesIO(path.read_bytes()))
        order = tt.getGlyphOrder()
        try:
            cmap = dict(tt.getBestCmap()) if "cmap" in tt else {}
        except Exception:  # noqa: BLE001 - unreadable cmap is rebuilt from scratch
            cmap = {}

        changed = False
        for codepoint, glyph_counts in usage.items():
            if codepoint < 32 or codepoint == 0xFFFD:
                continue
            glyph_id, _count = glyph_counts.most_common(1)[0]
            if not 0 <= glyph_id < len(order):
                continue
            glyph_name = order[glyph_id]
            if cmap.get(codepoint) != glyph_name:
                cmap[codepoint] = glyph_name
                changed = True

        if not changed:
            return
        builder = FontBuilder(font=tt)
        builder.setupCharacterMap(cmap)
        if "post" not in tt:
            builder.setupPost()
        buffer = io.BytesIO()
        tt.save(buffer)
        path.write_bytes(buffer.getvalue())
        logger.info("cmap reconciled from texttrace for %s (%s mappings)", font.original_name, len(usage))
    except Exception:  # noqa: BLE001 - reconciliation is best-effort hardening
        logger.warning("cmap reconciliation failed for %s", font.original_name, exc_info=True)


# Characters that legitimately map to blank glyphs — purging these would be
# wrong (the browser must render them as the font's own whitespace).
_EXPECTED_BLANK_CODEPOINTS = {0x09, 0x0A, 0x0D, 0x20, 0xA0, 0x2007, 0x2009, 0x200A, 0x200B, 0x2060, 0xFEFF}


def _purge_blank_mappings(fonts_dir: Path, fonts: list[FontResource]) -> dict[str, int]:
    """Character Fidelity guarantee: a cmap entry that maps a NON-whitespace
    character to an EMPTY glyph is never left in a served font.

    An empty-but-mapped glyph is the one failure mode browsers cannot save:
    per-character font fallback only triggers when the cmap has NO entry —
    a mapped blank paints as *nothing* (seen live: "much"→"mu h",
    "couldn't"→" ouldn't"). Runs AFTER the sibling-subset merge (which fills
    every outline it has a donor for); whatever is still blank has no
    recoverable outline in any sibling, so the honest behavior is to unmap
    it — the character then renders visibly in the stack's fallback font
    and is counted as a SUBSTITUTION in the fidelity report, never lost.

    Returns {font_id: purged_count} for the report."""
    purged_by_font: dict[str, int] = {}
    for resource in fonts:
        if not resource.filename or not resource.filename.endswith(".ttf"):
            continue  # CFF wrapped fonts are rebuilt from real outlines
        try:
            path = fonts_dir / resource.filename
            tt = TTFont(io.BytesIO(path.read_bytes()))
            if "glyf" not in tt or "cmap" not in tt:
                continue
            glyf = tt["glyf"]
            cmap_map = dict(tt.getBestCmap() or {})
            to_purge = [
                codepoint
                for codepoint, glyph_name in cmap_map.items()
                if codepoint not in _EXPECTED_BLANK_CODEPOINTS and _is_empty_glyph(glyf, glyph_name)
            ]
            if not to_purge:
                continue
            for codepoint in to_purge:
                del cmap_map[codepoint]
            builder = FontBuilder(font=tt)
            builder.setupCharacterMap(cmap_map or {0x20: tt.getGlyphOrder()[0]})
            buffer = io.BytesIO()
            tt.save(buffer)
            path.write_bytes(buffer.getvalue())
            purged_by_font[resource.id] = len(to_purge)
            logger.info(
                "character-fidelity purge: %s unmapped %s blank glyphs (%s) — these chars now render via fallback, never invisibly",
                resource.original_name,
                len(to_purge),
                "".join(chr(c) for c in sorted(to_purge)[:12]),
            )
        except Exception:  # noqa: BLE001 - purging is protective hardening; never fail the stage
            logger.warning("character-fidelity purge failed for %s", resource.original_name, exc_info=True)
    return purged_by_font


def _is_empty_glyph(glyf_table, glyph_name: str) -> bool:
    glyph = glyf_table.glyphs.get(glyph_name)
    if glyph is None:
        return True
    glyph.expand(glyf_table)
    return getattr(glyph, "numberOfContours", 0) == 0


def _complete_sibling_subsets(fonts_dir: Path, fonts: list[FontResource]) -> None:
    """PDFs routinely embed SEVERAL subsets of the same typeface, cut from
    the same base font (identical glyph count/order) with the real outlines
    PARTITIONED between them — subset A has the glyphs pages 1–3 used,
    subset B the rest, and both keep empty placeholders for the others'.
    The PDF stitches them per text run; the browser cannot (an "existing
    but empty" glyph renders as nothing — seen as dropped letters: 'just
    going' → 'ust oin').

    This pass makes every same-family TrueType subset COMPLETE: for each
    glyph index where one file has an empty outline and a sibling has a
    real one, copy the outline + advance across, and union the cmaps
    (translated by glyph index). Attribution then can't drop glyphs no
    matter which subset a span resolves to. Only simple (non-composite)
    glyphs are copied — composites reference component glyph NAMES, which
    aren't guaranteed to align between files. A missing post table (common
    in subsets, and required by browser sanitizers) is synthesized."""
    groups: dict[tuple[str, str], list[FontResource]] = {}
    for font in fonts:
        if font.filename and font.filename.endswith(".ttf"):
            groups.setdefault((font.family, font.style), []).append(font)

    for group in groups.values():
        if len(group) < 2:
            continue
        try:
            _merge_group(fonts_dir, group)
        except Exception:  # noqa: BLE001 - merging is best-effort hardening; never fail the stage
            logger.warning("sibling-subset merge failed for family=%s", group[0].family, exc_info=True)


def _merge_group(fonts_dir: Path, group: list[FontResource]) -> None:
    loaded: list[tuple[FontResource, TTFont]] = []
    for resource in group:
        loaded.append((resource, TTFont(io.BytesIO((fonts_dir / resource.filename).read_bytes()))))

    # Safety: only merge files that are demonstrably cuts of the same base
    # font — same glyph count and same units-per-em.
    reference = loaded[0][1]
    if "glyf" not in reference:
        return
    glyph_count = reference["maxp"].numGlyphs
    upm = reference["head"].unitsPerEm
    for _, tt in loaded[1:]:
        if "glyf" not in tt or tt["maxp"].numGlyphs != glyph_count or tt["head"].unitsPerEm != upm:
            logger.info("sibling-subset merge skipped for %s: not same base font", group[0].family)
            return

    orders = [tt.getGlyphOrder() for _, tt in loaded]
    cmaps: list[dict[int, str]] = []
    for _, tt in loaded:
        try:
            cmaps.append(dict(tt.getBestCmap()) if "cmap" in tt else {})
        except Exception:  # noqa: BLE001 - a broken cmap is treated as absent and rebuilt below
            cmaps.append({})

    copied = 0
    for target_index, (_, target) in enumerate(loaded):
        target_glyf = target["glyf"]
        target_hmtx = target["hmtx"]
        for source_index, (_, source) in enumerate(loaded):
            if source_index == target_index:
                continue
            source_glyf = source["glyf"]
            source_hmtx = source["hmtx"]
            for i in range(glyph_count):
                target_name = orders[target_index][i]
                source_name = orders[source_index][i]
                if not _is_empty_glyph(target_glyf, target_name):
                    continue
                source_glyph = source_glyf.glyphs.get(source_name)
                if source_glyph is None:
                    continue
                source_glyph.expand(source_glyf)
                contours = getattr(source_glyph, "numberOfContours", 0)
                if contours <= 0:  # empty, or composite (name-space mismatch risk)
                    continue
                target_glyf.glyphs[target_name] = copy.deepcopy(source_glyph)
                if target_name in target_hmtx.metrics and source_name in source_hmtx.metrics:
                    if target_hmtx.metrics[target_name][0] == 0 and source_hmtx.metrics[source_name][0] > 0:
                        target_hmtx.metrics[target_name] = source_hmtx.metrics[source_name]
                copied += 1

        # Union cmaps, translated through glyph indices.
        index_of = {name: i for i, name in enumerate(orders[target_index])}
        merged_cmap = dict(cmaps[target_index])
        for source_index in range(len(loaded)):
            if source_index == target_index:
                continue
            source_order_index = {name: i for i, name in enumerate(orders[source_index])}
            for codepoint, source_name in cmaps[source_index].items():
                i = source_order_index.get(source_name)
                if i is None or codepoint in merged_cmap:
                    continue
                merged_cmap[codepoint] = orders[target_index][i]
        del index_of  # index translation happens through orders directly

        builder = FontBuilder(font=target)
        if merged_cmap:
            builder.setupCharacterMap(merged_cmap)
        if "post" not in target:
            builder.setupPost()

    for resource, tt in loaded:
        buffer = io.BytesIO()
        tt.save(buffer)
        (fonts_dir / resource.filename).write_bytes(buffer.getvalue())

    logger.info(
        "sibling-subset merge for family=%s: %s files, %s outlines completed",
        group[0].family,
        len(loaded),
        copied,
    )


class ExtractFontsStage(Stage):
    """Discovers every font used across the document, deduplicated by PDF
    xref, and writes embedded font files to resources/fonts/. Populates
    context.document.fonts and two scratch registries ExtractTextStage uses
    to resolve a text span's font name to a FontResource id."""

    def __init__(self, storage_service: StorageService) -> None:
        self._storage = storage_service

    @property
    def name(self) -> str:
        return PipelineStage.EXTRACT_FONTS.value

    def run(self, context: PipelineContext) -> None:
        assert context.document is not None, "MetadataStage must run before ExtractFontsStage"
        fonts_dir = self._storage.fonts_dir(context.project_id)
        font_by_xref: dict[int, FontResource] = {}
        font_id_by_name: dict[str, str] = {}
        # unicode -> Counter(glyph id -> occurrences) the PDF actually
        # rendered, per font xref (collected from texttrace; used to
        # reconcile file cmaps below). A codepoint can legitimately render
        # through MORE THAN ONE glyph id across a document — e.g. a
        # deliberate InDesign stylistic-alternate substitution used on only
        # some occurrences of a letter to avoid visual repetition (Issue
        # 005, 2026-07-14: 's' rendered via both its standard glyph and a
        # '.salt' alternate in the same word). A cmap can only hold ONE
        # glyph per codepoint, so every occurrence is counted and the
        # MAJORITY glyph wins — never "whichever was processed last".
        usage_by_xref: dict[int, dict[int, Counter]] = {}

        with fitz.open(context.source_pdf_path) as pdf:
            for index, pdf_page in enumerate(pdf, start=1):
                started = time.perf_counter()
                new_fonts_on_page = 0
                try:
                    page_fonts = pdf_page.get_fonts(full=False)
                except Exception:  # noqa: BLE001 - one bad page must not abort the whole document
                    logger.warning("page=%s extract_fonts failed", index, exc_info=True)
                    continue

                for xref, ext, _subtype, basefont, _resource_name, encoding in page_fonts:
                    if xref in font_by_xref:
                        continue

                    is_subset = bool(_SUBSET_PREFIX.match(basefont))
                    family = _SUBSET_PREFIX.sub("", basefont) or basefont
                    lowered = family.lower()
                    weight = _weight_from_name(lowered)
                    style = "italic" if ("italic" in lowered or "oblique" in lowered) else "normal"

                    try:
                        font_ext, content = _extract_font_buffer(pdf, xref)
                    except Exception:  # noqa: BLE001 - non-embedded/base-14 fonts may not be extractable
                        font_ext, content = ext, b""

                    filename = None
                    web_safe_content = None
                    web_ext = font_ext
                    if content:
                        if font_ext in _WEB_FONT_EXTENSIONS:
                            web_safe_content = _sanitize_for_web(font_ext, content, family)
                        elif font_ext == "cff":
                            web_safe_content = _wrap_bare_cff(content, family)
                            web_ext = "otf"
                            if web_safe_content:
                                logger.info("page=%s wrapped bare CFF font %s into OTF", index, basefont)
                    if web_safe_content:
                        filename = f"{uuid.uuid4()}.{web_ext}"
                        (fonts_dir / filename).write_bytes(web_safe_content)

                    font = FontResource(
                        id=str(uuid.uuid4()),
                        original_name=basefont,
                        family=family,
                        weight=weight,
                        style=style,
                        embedded=bool(web_safe_content),
                        subset=is_subset,
                        encoding=encoding or None,
                        filename=filename,
                    )
                    font_by_xref[xref] = font
                    # get_fonts() returns the subset-prefixed basefont (e.g.
                    # "MVTANU+QikkiReg"), but get_text("dict") span names
                    # strip that prefix (e.g. "QikkiReg") — register both so
                    # ExtractTextStage's lookup matches either form.
                    font_id_by_name[basefont] = font.id
                    font_id_by_name[family] = font.id
                    context.document.fonts.append(font)
                    new_fonts_on_page += 1

                page = context.document.get_page(index)
                if page is not None:
                    page.fonts_used = [font_by_xref[x].id for x in {f[0] for f in page_fonts} if x in font_by_xref]

                # Collect the ground-truth character→glyph pairs this page
                # rendered. Span font names come back bare (no subset
                # prefix), so candidates are matched on either form.
                try:
                    traces = pdf_page.get_texttrace()
                except Exception:  # noqa: BLE001 - diagnostics source only; never abort the page
                    traces = []
                names_to_xrefs: dict[str, list[int]] = {}
                for xref, _ext, _subtype, basefont, _res, _enc in page_fonts:
                    for key in (basefont, _SUBSET_PREFIX.sub("", basefont)):
                        names_to_xrefs.setdefault(key, []).append(xref)
                for span in traces:
                    for xref in names_to_xrefs.get(span.get("font", ""), []):
                        usage = usage_by_xref.setdefault(xref, {})
                        for char in span.get("chars", []):
                            usage.setdefault(char[0], Counter())[char[1]] += 1

                logger.info(
                    "page=%s extract_fonts new_fonts=%s duration_ms=%.1f",
                    index,
                    new_fonts_on_page,
                    (time.perf_counter() - started) * 1000,
                )

        # After every subset is on disk: first reconcile each file's cmap
        # with what the PDF actually rendered (custom-encoded subsets), then
        # make same-family sibling subsets complete (outline partitioning is
        # invisible per-file — it only shows up as dropped glyphs once a
        # browser renders the overlay).
        for xref, usage in usage_by_xref.items():
            font = font_by_xref.get(xref)
            if font and font.filename and font.filename.endswith((".ttf", ".otf")):
                _reconcile_cmap_from_usage(fonts_dir, font, usage)
        _complete_sibling_subsets(fonts_dir, context.document.fonts)
        # Character Fidelity guarantee (runs LAST): any mapping the merge
        # couldn't rescue is unmapped so the browser falls back visibly —
        # a character can be substituted, never silently lost.
        context.scratch["fidelity_purged_mappings"] = _purge_blank_mappings(fonts_dir, context.document.fonts)

        context.scratch["font_id_by_name"] = font_id_by_name
