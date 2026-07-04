import { logViewerEvent } from "./diagnostics";
import { EventBus } from "./EventBus";
import { IframeRenderer } from "./IframeRenderer";
import { NavigationManager } from "./NavigationManager";
import { Selection } from "./Selection";
import { AccuracySettings, DiagnosticsSnapshot, ViewerEvents, ViewerPage, ViewerState, ViewMode, ZoomState } from "./types";
import { Viewport } from "./Viewport";
import { ZoomManager } from "./ZoomManager";

interface MountedPage {
  renderer: IframeRenderer;
  selection: Selection;
}

/** Hard resource cap on simultaneously mounted page iframes (Large Document
 * Architecture, docs/ARCHITECTURE.md). The active window must always fit
 * inside it; the headroom keeps recently-read neighbors mounted so paging
 * back is instant. */
export const MAX_MOUNTED_PAGES = 9;

/** The viewer's foundation: PreviewPane stays a thin React shell that asks
 * this engine to open a document, mount/unmount page hosts, navigate, and
 * change zoom — all rendering, loading, and selection logic lives here so
 * it's reusable outside React (and ready to grow into an editor later).
 *
 * Deliberately project-agnostic: it knows only about `ViewerPage`s (page
 * geometry + a resolved `html_url`), never about Project, Job, Manifest, or
 * Statistics concepts. Resolving *which* project's pages to open, and turning
 * their relative storage paths into fetchable URLs, is the WorkspaceService's
 * job — that keeps this engine reusable for any future page source.
 *
 * Rendering uses a same-origin <iframe> per page (see IframeRenderer): the
 * one rendering path shared by direct-open, served, and preview, so the
 * preview is guaranteed to match a page opened directly in a browser.
 *
 * `state` is the single state machine that controls the viewer (deliberately
 * not a scatter of booleans): idle -> opening_project -> loading_assets ->
 * rendering -> ready, or -> error at any step. */
export class ViewerEngine {
  readonly bus = new EventBus<ViewerEvents>();
  readonly navigation: NavigationManager;
  readonly zoom: ZoomManager;
  readonly viewport = new Viewport(1);

  private pages: ViewerPage[] = [];
  private mounted = new Map<number, MountedPage>();
  // Bumped synchronously on every mountPage() call for a given page so a
  // stale, still-in-flight call (e.g. React StrictMode double-invoking the
  // mount effect in dev) can detect it's no longer the latest attempt and
  // abort instead of appending a second iframe into the same host.
  private mountGenerations = new Map<number, number>();

  private state: ViewerState = "idle";
  private statePage: number | null = null;
  private lastError: string | null = null;
  private missingAssets = new Set<string>();
  private accuracySettings: AccuracySettings = { mode: "combined", overlayOpacity: 100 };

  // The contiguous strip of pages that should currently be mounted: the
  // active window around the anchor, extended by recently-read neighbors up
  // to MAX_MOUNTED_PAGES. Contiguity is a hard invariant — the continuous
  // canvas stacks these hosts, so a gap would visually splice distant pages
  // together. Eviction drops the pages farthest from the anchor, which for
  // linear reading is exactly the least-recently-visible end; a long jump
  // discards the old strip wholesale (it is entirely least-recent).
  private strip: number[] = [];

  private viewMode: ViewMode = "continuous";

  // Search jump-highlight: the target page may not be mounted yet when the
  // jump happens, so the highlight is applied on that page's PageRendered.
  private pendingHighlight: { page: number; objectId: string } | null = null;
  private activeHighlight: { element: HTMLElement; prevOutline: string; prevOffset: string } | null = null;

  constructor() {
    this.navigation = new NavigationManager(this.bus, 0);
    this.zoom = new ZoomManager(this.bus);
    this.bus.on("PageChanged", ({ page }) => this.syncWindow(page));
    this.bus.on("PageRendered", ({ page }) => {
      if (this.pendingHighlight?.page === page) {
        const { objectId } = this.pendingHighlight;
        this.pendingHighlight = null;
        this.applyHighlight(page, objectId);
      }
    });
  }

  get pageList(): ViewerPage[] {
    return this.pages;
  }

  getDiagnostics(): DiagnosticsSnapshot {
    return {
      state: this.state,
      statePage: this.statePage,
      mountedPages: [...this.mounted.keys()].sort((a, b) => a - b),
      missingAssets: [...this.missingAssets],
      lastError: this.lastError,
    };
  }

  private setState(state: ViewerState, page: number | null, error?: string): void {
    this.state = state;
    this.statePage = page;
    if (error) this.lastError = error;
    this.bus.emit("StateChanged", { state, page, error });
    this.bus.emit("DiagnosticsChanged", this.getDiagnostics());
  }

  openDocument(pages: ViewerPage[]): void {
    this.unmountAll();
    this.missingAssets.clear();
    this.lastError = null;
    this.strip = [];
    this.setState("opening_project", null);

    this.pages = [...pages].sort((a, b) => a.page_number - b.page_number);
    this.navigation.setPageCount(this.pages.length);
    // jumpTo(1) is a no-op when we're already on page 1, so sync explicitly.
    this.navigation.jumpTo(1);
    this.syncWindow(this.navigation.currentPage);
    this.bus.emit("DocumentOpened", { pageCount: this.pages.length });

    this.setState("idle", null);
  }

  get currentViewMode(): ViewMode {
    return this.viewMode;
  }

  /** Switching mode resets the strip (spread modes never accumulate
   * neighbors) and re-syncs around the current page. */
  setViewMode(mode: ViewMode): void {
    if (mode === this.viewMode) return;
    this.viewMode = mode;
    this.strip = [];
    this.bus.emit("ViewModeChanged", { mode });
    this.syncWindow(this.navigation.currentPage);
  }

  /** The spread a page belongs to under the current view mode. */
  spreadFor(page: number, mode: ViewMode = this.viewMode): number[] {
    const count = this.pages.length;
    const clamp = (pages: number[]) => pages.filter((p) => p >= 1 && p <= count);
    if (mode === "facing") {
      const start = page % 2 === 1 ? page : page - 1;
      return clamp([start, start + 1]);
    }
    if (mode === "book") {
      if (page === 1) return clamp([1]);
      const start = page % 2 === 0 ? page : page - 1;
      return clamp([start, start + 1]);
    }
    return clamp([page]);
  }

  /** Groups a mounted strip into layout rows for the canvas: one page per
   * row in continuous/single, spread pairs in facing/book. */
  groupIntoSpreads(pages: number[]): number[][] {
    if (this.viewMode !== "facing" && this.viewMode !== "book") {
      return pages.map((page) => [page]);
    }
    const rows: number[][] = [];
    const seen = new Set<number>();
    for (const page of pages) {
      if (seen.has(page)) continue;
      const spread = this.spreadFor(page).filter((p) => pages.includes(p));
      spread.forEach((p) => seen.add(p));
      rows.push(spread);
    }
    return rows;
  }

  /** The active mount window — what MUST be mounted for an anchor page
   * under the current view mode. */
  computeWindow(anchor: number): number[] {
    switch (this.viewMode) {
      case "single":
        return this.pages.length > 0 ? [Math.min(Math.max(1, anchor), this.pages.length)] : [];
      case "facing":
      case "book":
        return this.spreadFor(anchor);
      case "continuous":
      default:
        return this.viewport.pagesToMount(anchor, this.pages.length);
    }
  }

  /** Reconciles the mounted strip with a new anchor and emits WindowChanged.
   * The strip is the window plus retained contiguous neighbors, hard-capped
   * at MAX_MOUNTED_PAGES (see the field comment for the eviction policy). */
  syncWindow(anchor: number): number[] {
    const window = this.computeWindow(anchor);
    if (window.length === 0) {
      this.strip = [];
      this.bus.emit("WindowChanged", { pages: [] });
      return [];
    }

    // Only continuous mode retains neighbors — single/facing/book mount
    // exactly their window (a spread is its own complete layout unit).
    if (this.viewMode !== "continuous") {
      this.strip = [...window];
      this.bus.emit("WindowChanged", { pages: [...window] });
      return [...window];
    }

    const wMin = window[0];
    const wMax = window[window.length - 1];
    let min = wMin;
    let max = wMax;

    if (this.strip.length > 0) {
      const oldMin = this.strip[0];
      const oldMax = this.strip[this.strip.length - 1];
      const disjoint = wMin > oldMax + 1 || wMax < oldMin - 1;
      if (!disjoint) {
        min = Math.min(min, oldMin);
        max = Math.max(max, oldMax);
      }
    }

    // Trim to the cap by dropping the end farthest from the anchor, but
    // never trim into the active window itself.
    while (max - min + 1 > MAX_MOUNTED_PAGES) {
      const dropHead = anchor - min > max - anchor;
      if (dropHead && min < wMin) min++;
      else if (max > wMax) max--;
      else min++;
    }

    const strip: number[] = [];
    for (let page = min; page <= max; page++) strip.push(page);
    this.strip = strip;
    this.bus.emit("WindowChanged", { pages: [...strip] });
    return [...strip];
  }

  /** The strip of pages the canvas should render hosts for right now. */
  pagesToMount(): number[] {
    return this.strip.length > 0 ? [...this.strip] : this.computeWindow(this.navigation.currentPage);
  }

  getPage(pageNumber: number): ViewerPage | undefined {
    return this.pages.find((p) => p.page_number === pageNumber);
  }

  async mountPage(pageNumber: number, host: HTMLElement): Promise<void> {
    const page = this.getPage(pageNumber);
    if (!page || !page.html_url) return;

    // Always start from a clean host: removes any tracked renderer AND
    // wipes the DOM directly, so a previous call's iframe can never remain
    // even if it hadn't been registered in `mounted` yet (still loading).
    this.unmountPage(pageNumber);
    host.innerHTML = "";

    const generation = (this.mountGenerations.get(pageNumber) ?? 0) + 1;
    this.mountGenerations.set(pageNumber, generation);
    const isStale = () => this.mountGenerations.get(pageNumber) !== generation;

    const renderer = new IframeRenderer(host);
    const selection = new Selection(this.bus);
    const url = page.html_url;

    try {
      this.setState("loading_assets", pageNumber);
      this.bus.emit("PageLoaded", { page: pageNumber });

      // load() resolves after the iframe document AND its fonts are ready,
      // so the very first visible paint uses the correct fonts.
      await renderer.load(url);

      // A newer mountPage() call for this same page started while we were
      // awaiting — it already owns the host now, so this attempt must not
      // touch shared state or leave its iframe behind.
      if (isStale()) {
        renderer.clear();
        return;
      }

      this.setState("rendering", pageNumber);
      renderer.applyAccuracySettings(this.accuracySettings);
      selection.attach(renderer.root, pageNumber);
      this.trackImageLoads(renderer, pageNumber);
      logViewerEvent("Iframe page mounted", { page: pageNumber });

      this.mounted.set(pageNumber, { renderer, selection });
      this.bus.emit("PageRendered", { page: pageNumber });
      this.setState("ready", pageNumber);
      logViewerEvent("Ready", { page: pageNumber });
    } catch (error) {
      if (isStale()) return; // a newer attempt superseded this one; ignore
      const message = error instanceof Error ? error.message : String(error);
      logViewerEvent("Error", { page: pageNumber, error: message });
      this.setState("error", pageNumber, message);
      throw error;
    }
  }

  /** Records any <img> inside the rendered page that failed to load, for
   * the debug panel. Best-effort and non-blocking — the iframe already
   * waited for its own load event before we get here. */
  private trackImageLoads(renderer: IframeRenderer, pageNumber: number): void {
    const doc = renderer.root;
    if (!doc) return;
    doc.querySelectorAll("img").forEach((img) => {
      if (img.complete) {
        if (img.naturalWidth === 0 && img.src) this.recordMissingAsset(img.src, pageNumber);
        return;
      }
      img.addEventListener("error", () => this.recordMissingAsset(img.src, pageNumber));
    });
  }

  private recordMissingAsset(src: string, pageNumber: number): void {
    this.missingAssets.add(src);
    logViewerEvent("Missing Asset", { page: pageNumber, src });
    this.bus.emit("DiagnosticsChanged", this.getDiagnostics());
  }

  unmountPage(pageNumber: number): void {
    const entry = this.mounted.get(pageNumber);
    if (!entry) return;
    entry.selection.clear();
    entry.renderer.clear();
    this.mounted.delete(pageNumber);
  }

  unmountAll(): void {
    for (const pageNumber of [...this.mounted.keys()]) this.unmountPage(pageNumber);
  }

  /** Outlines an object inside its rendered page (search jump). Uses the
   * same data-object-id identity as Selection and announces the object
   * through the same SelectionChanged event — one selection pipeline. If
   * the page isn't mounted yet the highlight applies on its PageRendered. */
  highlightObject(page: number, objectId: string): void {
    this.clearHighlight();
    if (this.mounted.has(page)) {
      this.applyHighlight(page, objectId);
    } else {
      this.pendingHighlight = { page, objectId };
    }
  }

  private applyHighlight(page: number, objectId: string): void {
    const entry = this.mounted.get(page);
    const root = entry?.renderer.root;
    if (!root) return;
    const element = root.querySelector(`[data-object-id="${objectId}"]`) as HTMLElement | null;
    if (!element) return;
    this.activeHighlight = {
      element,
      prevOutline: element.style.outline,
      prevOffset: element.style.outlineOffset,
    };
    // Inline values: --lf-* tokens don't exist inside the generated page's
    // document, and the page is never themed. #2f6fed == --lf-accent.
    element.style.outline = "2px solid #2f6fed";
    element.style.outlineOffset = "2px";
    element.scrollIntoView({ block: "center" });
    this.bus.emit("SelectionChanged", {
      objectId,
      type: element.dataset.type ?? "text",
      page,
    });
  }

  clearHighlight(): void {
    this.pendingHighlight = null;
    if (!this.activeHighlight) return;
    const { element, prevOutline, prevOffset } = this.activeHighlight;
    element.style.outline = prevOutline;
    element.style.outlineOffset = prevOffset;
    this.activeHighlight = null;
  }

  setZoomPercent(percent: number): void {
    this.zoom.setFixed(percent);
  }

  setZoomFit(mode: "fit-width" | "fit-page", viewportWidth: number, viewportHeight: number): void {
    const page = this.getPage(this.navigation.currentPage);
    if (!page) return;
    this.zoom.setFit(mode, viewportWidth, viewportHeight, page.width, page.height);
  }

  get currentZoom(): ZoomState {
    return this.zoom.current;
  }

  get currentAccuracySettings(): AccuracySettings {
    return this.accuracySettings;
  }

  /** Applies to every currently-mounted page immediately, and is
   * remembered so pages mounted later (e.g. after navigating) inherit it. */
  setAccuracySettings(settings: AccuracySettings): void {
    this.accuracySettings = settings;
    for (const entry of this.mounted.values()) {
      entry.renderer.applyAccuracySettings(settings);
    }
  }
}
