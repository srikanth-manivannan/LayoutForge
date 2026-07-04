import { useEffect, useRef, useState } from "react";

import { PageRead } from "../api/client";
import { PreviewError } from "../environment/PreviewError";
import { useViewerKeyboard } from "../hooks/useViewerKeyboard";
import { useViewerWindow } from "../hooks/useViewerWindow";
import { WorkspaceService } from "../workspace/WorkspaceService";
import { ViewerEngine } from "../viewer/ViewerEngine";
import { ViewMode } from "../viewer/types";
import { ZOOM_PRESETS } from "../viewer/ZoomManager";
import DevDiagnosticsPanel from "./DevDiagnosticsPanel";
import ThumbnailRail from "./ThumbnailRail";
import ViewerPageHost from "./ViewerPageHost";
import ViewerSearchBar from "./ViewerSearchBar";

interface PreviewPaneProps {
  engine: ViewerEngine;
  workspace: WorkspaceService;
  projectId: string | null;
  pages: PageRead[];
  pagesError: PreviewError | null;
}

/** `engine` is used only for rendering concerns (subscribing to its bus,
 * mounting page hosts) — every project-level action (opening pages, nav,
 * zoom) goes through `workspace` instead, per the ViewerEngine/WorkspaceService
 * split: the engine never resolves project ids or storage paths itself. */
const VIEW_MODES = [
  { value: "continuous", label: "Continuous" },
  { value: "single", label: "Single page" },
  { value: "facing", label: "Facing" },
  { value: "book", label: "Book" },
] as const;

export default function PreviewPane({ engine, workspace, projectId, pages, pagesError }: PreviewPaneProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageField, setPageField] = useState("1");
  const [zoomPercent, setZoomPercent] = useState(100);
  const [viewMode, setViewMode] = useState<ViewMode>("continuous");
  const [mountedPages, setMountedPages] = useState<number[]>([]);
  const [documentEpoch, setDocumentEpoch] = useState(0);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showRail, setShowRail] = useState(() => localStorage.getItem("lf.viewer.rail") !== "off");
  const containerRef = useRef<HTMLDivElement>(null);

  const toggleRail = () => {
    setShowRail((show) => {
      localStorage.setItem("lf.viewer.rail", show ? "off" : "on");
      return !show;
    });
  };
  // Set on programmatic navigation only — the strip may not have the target
  // host mounted yet, so the actual scrollIntoView happens in the effect
  // below once React has rendered the new strip.
  const pendingScrollRef = useRef<number | null>(null);

  const active = Boolean(projectId) && pages.length > 0;
  // Scroll-driven page promotion only makes sense in continuous mode —
  // single/facing/book mount exactly their layout unit.
  useViewerWindow(engine, containerRef, active && viewMode === "continuous");
  useViewerKeyboard(
    workspace,
    containerRef,
    active,
    () => setShowSearch(true),
    () => setShowDiagnostics((show) => !show),
  );

  useEffect(() => {
    // Every openDocument invalidates all mounted iframes (the engine
    // unmounts them) — bump the epoch so React remounts the hosts, which
    // re-runs their mountPage effects. Without this a re-open leaves
    // already-rendered hosts permanently blank.
    const offOpened = engine.bus.on("DocumentOpened", () => {
      setDocumentEpoch((epoch) => epoch + 1);
      setMountedPages(engine.pagesToMount());
    });
    const offPage = engine.bus.on("PageChanged", ({ page, source }) => {
      setCurrentPage(page);
      setPageField(String(page));
      if (source === "program") pendingScrollRef.current = page;
    });
    const offWindow = engine.bus.on("WindowChanged", ({ pages: strip }) => setMountedPages(strip));
    const offZoom = engine.bus.on("ZoomChanged", ({ percent }) => setZoomPercent(percent));
    const offMode = engine.bus.on("ViewModeChanged", ({ mode }) => setViewMode(mode));

    // Opening/closing the project in the WorkspaceService is the route's
    // job (WorkspacePage) — this pane only mirrors engine state, so it can
    // mount/unmount freely as center tabs switch.
    if (projectId && pages.length > 0) {
      setCurrentPage(engine.navigation.currentPage);
      setPageField(String(engine.navigation.currentPage));
      setZoomPercent(engine.currentZoom.percent);
      setViewMode(engine.currentViewMode);
      setMountedPages(engine.pagesToMount());
      // Re-anchor the canvas on the current page (returning from another
      // center tab mounts a fresh scroll container at scrollTop 0).
      pendingScrollRef.current = engine.navigation.currentPage;
    } else {
      setMountedPages([]);
    }

    return () => {
      offOpened();
      offPage();
      offWindow();
      offZoom();
      offMode();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, workspace, projectId, pages]);

  const commitPageField = () => {
    const parsed = Number(pageField);
    if (Number.isFinite(parsed) && parsed >= 1) workspace.navigateTo(Math.round(parsed));
    else setPageField(String(currentPage));
  };

  // After a programmatic jump, bring the target host into view once it
  // exists in the rendered strip (scroll-driven changes never scroll).
  useEffect(() => {
    const target = pendingScrollRef.current;
    if (target === null || target !== currentPage) return;
    const host = containerRef.current?.querySelector<HTMLElement>(`[data-lf-page-host="${target}"]`);
    if (host) {
      pendingScrollRef.current = null;
      host.scrollIntoView({ block: "start" });
    }
  }, [currentPage, mountedPages]);

  if (projectId && pagesError) {
    return (
      <main className="lf-preview d-flex align-items-center justify-content-center">
        <div className="alert alert-danger" style={{ maxWidth: 480 }}>
          <h6 className="alert-heading">Unable to load preview.</h6>
          <p className="mb-1">
            <strong>Reason:</strong> {pagesError.reason}
          </p>
          {pagesError.expected && (
            <p className="mb-1">
              <strong>Expected:</strong> <code>{pagesError.expected}</code>
            </p>
          )}
          <p className="mb-1">
            <strong>Suggestions:</strong>
          </p>
          <ul className="mb-0">
            {pagesError.suggestions.map((suggestion) => (
              <li key={suggestion}>{suggestion}</li>
            ))}
          </ul>
        </div>
      </main>
    );
  }

  if (!projectId || pages.length === 0) {
    return (
      <main className="lf-preview d-flex align-items-center justify-content-center">
        <p className="text-muted">Select a project to preview its reconstructed pages.</p>
      </main>
    );
  }

  return (
    <main className="lf-preview d-flex flex-column">
      <div className="lf-viewer-toolbar d-flex align-items-center gap-2 p-2 border-bottom lf-surface">
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          title="Previous page (PageUp)"
          onClick={() => workspace.navigatePrevious()}
        >
          ◀
        </button>
        <input
          className="form-control form-control-sm text-center"
          style={{ width: 52 }}
          value={pageField}
          aria-label="Page number"
          onChange={(event) => setPageField(event.target.value)}
          onBlur={commitPageField}
          onKeyDown={(event) => {
            if (event.key === "Enter") commitPageField();
          }}
        />
        <span className="small text-muted">/ {pages.length}</span>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          title="Next page (PageDown)"
          onClick={() => workspace.navigateNext()}
        >
          ▶
        </button>
        <span className="vr mx-1" />
        <select
          className="form-select form-select-sm w-auto"
          value={ZOOM_PRESETS.includes(zoomPercent as (typeof ZOOM_PRESETS)[number]) ? zoomPercent : ""}
          aria-label="Zoom"
          onChange={(event) => workspace.setZoomPercent(Number(event.target.value))}
        >
          {!ZOOM_PRESETS.includes(zoomPercent as (typeof ZOOM_PRESETS)[number]) && (
            <option value="" disabled>
              {Math.round(zoomPercent)}%
            </option>
          )}
          {ZOOM_PRESETS.map((preset) => (
            <option key={preset} value={preset}>
              {preset}%
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          title="Fit width (Ctrl+0)"
          onClick={() =>
            containerRef.current &&
            workspace.setZoomFit("fit-width", containerRef.current.clientWidth, containerRef.current.clientHeight)
          }
        >
          Fit W
        </button>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          title="Fit page"
          onClick={() =>
            containerRef.current &&
            workspace.setZoomFit("fit-page", containerRef.current.clientWidth, containerRef.current.clientHeight)
          }
        >
          Fit P
        </button>
        <span className="vr mx-1" />
        <select
          className="form-select form-select-sm w-auto"
          value={viewMode}
          aria-label="View mode"
          onChange={(event) => workspace.setViewMode(event.target.value as ViewMode)}
        >
          {VIEW_MODES.map((mode) => (
            <option key={mode.value} value={mode.value}>
              {mode.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          className={`btn btn-sm ${showRail ? "btn-secondary" : "btn-outline-secondary"} ms-auto`}
          title={showRail ? "Hide thumbnails" : "Show thumbnails"}
          onClick={toggleRail}
        >
          ▤
        </button>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          title="Search document (Ctrl+F)"
          onClick={() => setShowSearch((show) => !show)}
        >
          🔍
        </button>
      </div>
      {showSearch && projectId && (
        <ViewerSearchBar
          engine={engine}
          workspace={workspace}
          projectId={projectId}
          onClose={() => setShowSearch(false)}
        />
      )}
      <div className="d-flex flex-grow-1" style={{ minHeight: 0 }}>
        {showRail && (
          <ThumbnailRail
            pages={pages}
            currentPage={currentPage}
            resolveUrl={(path) => workspace.resolveStaticUrl(path)}
            onSelect={(pageNumber) => workspace.navigateTo(pageNumber)}
          />
        )}
        <div
          ref={containerRef}
          className="lf-viewer-canvas flex-grow-1 overflow-auto d-flex flex-column align-items-center gap-3 p-3"
        >
          {engine.groupIntoSpreads(mountedPages).map((spread) => (
            <div key={spread.join("-")} className="d-flex flex-row gap-3">
              {spread.map((pageNumber) => {
                const page = engine.getPage(pageNumber);
                if (!page) return null;
                return (
                  <ViewerPageHost
                    key={`${documentEpoch}-${pageNumber}`}
                    engine={engine}
                    pageNumber={pageNumber}
                    zoomPercent={zoomPercent}
                    pageWidth={page.width}
                    pageHeight={page.height}
                    isCurrent={pageNumber === currentPage}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
      {showDiagnostics && <DevDiagnosticsPanel engine={engine} zoomPercent={zoomPercent} />}
    </main>
  );
}
