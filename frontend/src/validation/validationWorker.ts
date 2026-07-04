/// <reference lib="webworker" />
/** Validation engine — runs entirely off the main thread (2C requirement:
 * cancelable, progressive, per-page). Fetches idm.json itself (same-origin
 * static mount) and posts findings page by page, so the panel can show
 * results streaming in; cancellation is Worker.terminate() from the owner.
 *
 * Every check reads ONLY the IDM (Principle: IDM is the source of truth)
 * and reports nothing it can't verify from it — disk/file health is the
 * backend summary's job, not ours. */

import type { IdmDocument, IdmFont, IdmPage } from "../document/idmTypes";
import type { ValidationFinding, WorkerRequest, WorkerResponse } from "./types";

const BOUNDS_TOLERANCE_PT = 2;

function post(message: WorkerResponse): void {
  (self as unknown as DedicatedWorkerGlobalScope).postMessage(message);
}

function checkPage(page: IdmPage, fontsById: Map<string, IdmFont>, assetIds: Set<string>): ValidationFinding[] {
  const findings: ValidationFinding[] = [];
  const reportedFonts = new Set<string>();

  for (const block of page.text_blocks) {
    const { x, y, width, height } = block.bbox;
    if (
      x < -BOUNDS_TOLERANCE_PT ||
      y < -BOUNDS_TOLERANCE_PT ||
      x + width > page.width + BOUNDS_TOLERANCE_PT ||
      y + height > page.height + BOUNDS_TOLERANCE_PT
    ) {
      findings.push({
        severity: "warning",
        category: "layout",
        page: page.number,
        objectId: block.id,
        message: `Text block extends outside the page bounds (${Math.round(x)}, ${Math.round(y)}, ${Math.round(width)}×${Math.round(height)})`,
      });
    }

    if (!block.text.trim()) {
      findings.push({
        severity: "warning",
        category: "text",
        page: page.number,
        objectId: block.id,
        message: "Empty text block extracted — check the source area for artwork text",
      });
    }

    if (block.font_id) {
      const font = fontsById.get(block.font_id);
      if (font && !font.filename && !reportedFonts.has(block.font_id)) {
        reportedFonts.add(block.font_id);
        findings.push({
          severity: "warning",
          category: "fonts",
          page: page.number,
          objectId: block.id,
          message: `Font "${font.family}" has no web font file — text renders in a fallback font (metrics may drift)`,
        });
      }
    }
  }

  for (const image of page.images) {
    if (!assetIds.has(image.asset_id)) {
      findings.push({
        severity: "error",
        category: "assets",
        page: page.number,
        objectId: image.id,
        message: `Image references missing asset ${image.asset_id}`,
      });
    }
    if (image.bbox.width <= 0 || image.bbox.height <= 0) {
      findings.push({
        severity: "warning",
        category: "layout",
        page: page.number,
        objectId: image.id,
        message: "Image has a zero-size bounding box",
      });
    }
  }

  return findings;
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  if (event.data.type !== "run") return;
  try {
    const response = await fetch(event.data.idmUrl);
    if (!response.ok) throw new Error(`idm.json fetch failed (status ${response.status})`);
    const idm = (await response.json()) as IdmDocument;

    const fontsById = new Map(idm.fonts.map((font) => [font.id, font]));
    const assetIds = new Set(idm.assets.map((asset) => asset.id));
    const pageCount = idm.pages.length;

    for (const page of idm.pages) {
      const findings = checkPage(page, fontsById, assetIds);
      post({ type: "progress", page: page.number, pageCount, findings });
      // Yield so a terminate() lands between pages on huge documents.
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    post({ type: "done", pageCount });
  } catch (error) {
    post({ type: "error", message: error instanceof Error ? error.message : String(error) });
  }
};
