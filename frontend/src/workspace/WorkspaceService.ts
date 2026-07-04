import { PageRead } from "../api/client";
import { ViewerEngine } from "../viewer/ViewerEngine";
import { ViewerPage, ViewMode } from "../viewer/types";

const STATIC_ROOT = "/static/projects";

/** The seam between UI/Commands and the ViewerEngine. Owns exactly what the
 * engine must NOT know: which project is currently open, and how a page's
 * storage-relative `html_path` resolves to a fetchable URL. Every command
 * that touches the viewer runs through here (not the engine directly) —
 * today that's just navigation/zoom pass-throughs, but this is also where
 * future document-aware commands (export, validate, delete-page) attach
 * without ever teaching the engine about projects. */
export class WorkspaceService {
  private currentProjectId: string | null = null;

  constructor(private readonly engine: ViewerEngine) {}

  get projectId(): string | null {
    return this.currentProjectId;
  }

  openProject(projectId: string, pages: PageRead[]): void {
    // Re-opening the same document is destructive (openDocument unmounts
    // every live iframe, and React hosts don't know to remount) — skip
    // when nothing changed. Effects legitimately re-fire with a fresh but
    // identical pages array (route-level open + polling identity churn).
    if (
      this.currentProjectId === projectId &&
      this.engine.pageList.length === pages.length &&
      pages.length > 0
    ) {
      return;
    }
    this.currentProjectId = projectId;
    const resolved: ViewerPage[] = pages.map((page) => ({
      page_number: page.page_number,
      width: page.width,
      height: page.height,
      rotation: page.rotation,
      html_url: page.html_path ? `${STATIC_ROOT}/${projectId}/${page.html_path}` : null,
    }));
    this.engine.openDocument(resolved);
  }

  closeProject(): void {
    this.currentProjectId = null;
    this.engine.unmountAll();
  }

  /** Resolves a storage-relative asset path (e.g. a page's
   * `background_image`) to a fetchable URL for the currently open project.
   * Kept here — with openProject's html_path resolution — so no component
   * ever assembles static-mount URLs itself. */
  resolveStaticUrl(path: string | null): string | null {
    if (!path || !this.currentProjectId) return null;
    return `${STATIC_ROOT}/${this.currentProjectId}/${path}`;
  }

  navigateFirst(): void {
    this.engine.navigation.first();
  }

  navigatePrevious(): void {
    this.engine.navigation.previous();
  }

  navigateNext(): void {
    this.engine.navigation.next();
  }

  navigateLast(): void {
    this.engine.navigation.last();
  }

  navigateTo(page: number): void {
    this.engine.navigation.jumpTo(page);
  }

  setZoomPercent(percent: number): void {
    this.engine.setZoomPercent(percent);
  }

  setZoomFit(mode: "fit-width" | "fit-page", viewportWidth: number, viewportHeight: number): void {
    this.engine.setZoomFit(mode, viewportWidth, viewportHeight);
  }

  zoomIn(): void {
    this.engine.zoom.zoomIn();
  }

  zoomOut(): void {
    this.engine.zoom.zoomOut();
  }

  setViewMode(mode: ViewMode): void {
    this.engine.setViewMode(mode);
  }
}
