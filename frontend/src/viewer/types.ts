/** The engine's page shape deliberately knows nothing about projects: no
 * project id, no relative storage path. `html_url` is a fully-resolved,
 * ready-to-fetch URL — resolving it from a project id + relative path is the
 * WorkspaceService's job, not the engine's, so the engine stays reusable for
 * any future page source (a different project, a diff view, a plugin). */
export interface ViewerPage {
  page_number: number;
  width: number;
  height: number;
  rotation: number;
  html_url: string | null;
}

export type ZoomMode = "fixed" | "fit-width" | "fit-page";

/** How pages are laid out on the canvas. `continuous` scrolls a windowed
 * strip; `single` shows exactly one page; `facing` shows 2-up spreads
 * [1,2][3,4]…; `book` keeps the cover alone: [1][2,3][4,5]… */
export type ViewMode = "continuous" | "single" | "facing" | "book";

/** The one state machine that controls the viewer (per the stabilization
 * directive: no scattered booleans). Reflects the lifecycle of whichever
 * page is currently being opened/mounted. */
export type ViewerState = "idle" | "opening_project" | "loading_assets" | "rendering" | "ready" | "error";

/** Drives the Accuracy Debug View: isolates the background raster from
 * the extracted-text/image overlay so a layout mismatch is visually
 * obvious instead of guessed at. */
export type AccuracyMode = "combined" | "background-only" | "overlay-only";

export interface AccuracySettings {
  mode: AccuracyMode;
  overlayOpacity: number; // 0-100, only meaningful in "combined" mode
}

export interface DiagnosticsSnapshot {
  state: ViewerState;
  statePage: number | null;
  mountedPages: number[];
  missingAssets: string[];
  lastError: string | null;
}

export interface ZoomState {
  mode: ZoomMode;
  percent: number; // effective zoom, always populated (computed for fit-* modes)
}

export interface SelectionInfo {
  objectId: string;
  type: string; // "text" | "image" | "shape"
  page: number;
}

/** Who initiated a page change: "program" = buttons/commands/go-to (the
 * canvas should scroll the page into view); "scroll" = the user scrolling
 * (the canvas must NOT scroll — that would fight the user's gesture). */
export type NavigationSource = "program" | "scroll";

export interface ViewerEvents {
  DocumentOpened: { pageCount: number };
  PageLoaded: { page: number };
  PageRendered: { page: number };
  PageChanged: { page: number; source: NavigationSource };
  /** The contiguous strip of pages that should currently be mounted
   * (window around the anchor + LRU-retained neighbors, capped). */
  WindowChanged: { pages: number[] };
  ViewModeChanged: { mode: ViewMode };
  ZoomChanged: ZoomState;
  SelectionChanged: SelectionInfo | null;
  StateChanged: { state: ViewerState; page: number | null; error?: string };
  DiagnosticsChanged: DiagnosticsSnapshot;
}
