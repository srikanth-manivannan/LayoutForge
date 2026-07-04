import { useEffect, useState } from "react";

import { PageRead } from "../api/client";
import { Button, Slider, Toolbar, ToolbarSeparator, ToolbarSpacer } from "../components/ui";
import ViewerPageHost from "../components/ViewerPageHost";
import { AccuracyMode } from "../viewer/types";
import { ViewerEngine } from "../viewer/ViewerEngine";
import { WorkspaceService } from "../workspace/WorkspaceService";

type CompareLayout = "overlay" | "split";

const LAYER_MODES: { value: AccuracyMode; label: string }[] = [
  { value: "combined", label: "Combined" },
  { value: "background-only", label: "Background only" },
  { value: "overlay-only", label: "Overlay only" },
];

interface ComparePanelProps {
  engine: ViewerEngine;
  workspace: WorkspaceService;
  pages: PageRead[];
}

/** The production proofing tool (2C) — successor of the Layout Accuracy
 * phase's AccuracyDebugView, now a first-class center panel.
 *
 * Overlay: one live page with the reconstruction stacked on the source
 * raster; the opacity slider and layer isolation (combined / background /
 * overlay) ride the engine's existing applyAccuracySettings path.
 * Split: source raster and reconstruction side by side in ONE scroll
 * container, so pan stays synchronized by construction.
 *
 * Inherits current page and zoom from the shared engine — switching modes
 * never loses proofing context (the inner-loop rule). */
export default function ComparePanel({ engine, workspace, pages }: ComparePanelProps) {
  const [layout, setLayout] = useState<CompareLayout>("overlay");
  const [layerMode, setLayerMode] = useState<AccuracyMode>("combined");
  const [opacity, setOpacity] = useState(engine.currentAccuracySettings.overlayOpacity);
  const [currentPage, setCurrentPage] = useState(engine.navigation.currentPage);
  const [zoomPercent, setZoomPercent] = useState(engine.currentZoom.percent);

  useEffect(() => {
    const offPage = engine.bus.on("PageChanged", ({ page }) => setCurrentPage(page));
    const offZoom = engine.bus.on("ZoomChanged", ({ percent }) => setZoomPercent(percent));
    return () => {
      offPage();
      offZoom();
      // Leaving Compare must never leave the Viewer in an isolation mode.
      engine.setAccuracySettings({ mode: "combined", overlayOpacity: 100 });
    };
  }, [engine]);

  const applyLayer = (mode: AccuracyMode, nextOpacity: number) => {
    setLayerMode(mode);
    setOpacity(nextOpacity);
    engine.setAccuracySettings({ mode, overlayOpacity: nextOpacity });
  };

  const page = pages.find((p) => p.page_number === currentPage);
  const enginePage = engine.getPage(currentPage);
  const backgroundUrl = page ? workspace.resolveStaticUrl(page.background_image) : null;
  const scale = zoomPercent / 100;

  if (!enginePage) {
    return <div className="lf-empty p-4 text-muted small">Open a project to compare pages.</div>;
  }

  return (
    <div className="d-flex flex-column h-100">
      <Toolbar aria-label="Compare tools" className="flex-wrap">
        <div role="group" aria-label="Compare layout" className="d-inline-flex">
          <Button size="sm" variant={layout === "overlay" ? "primary" : "secondary"} onClick={() => setLayout("overlay")}>
            Overlay
          </Button>
          <Button size="sm" variant={layout === "split" ? "primary" : "secondary"} onClick={() => setLayout("split")}>
            Split
          </Button>
        </div>
        <ToolbarSeparator />
        <Button size="sm" variant="ghost" title="Previous page" onClick={() => workspace.navigatePrevious()}>
          ◀
        </Button>
        <span className="small text-muted">
          {currentPage} / {pages.length}
        </span>
        <Button size="sm" variant="ghost" title="Next page" onClick={() => workspace.navigateNext()}>
          ▶
        </Button>
        {layout === "overlay" && (
          <>
            <ToolbarSeparator />
            <span className="small text-muted">Reconstruction opacity</span>
            <Slider
              aria-label="Reconstruction opacity"
              min={0}
              max={100}
              value={opacity}
              onChange={(value) => applyLayer("combined", value)}
              formatValue={(value) => `${value}%`}
            />
            <ToolbarSeparator />
            <select
              className="lf-select form-select form-select-sm w-auto"
              aria-label="Layer isolation"
              value={layerMode}
              onChange={(event) => applyLayer(event.target.value as AccuracyMode, opacity)}
            >
              {LAYER_MODES.map((mode) => (
                <option key={mode.value} value={mode.value}>
                  {mode.label}
                </option>
              ))}
            </select>
          </>
        )}
        <ToolbarSpacer />
        <span className="small text-muted">{Math.round(zoomPercent)}%</span>
      </Toolbar>

      {layout === "overlay" ? (
        <div className="lf-viewer-canvas flex-grow-1 overflow-auto d-flex flex-column align-items-center p-3">
          <ViewerPageHost
            engine={engine}
            pageNumber={currentPage}
            zoomPercent={zoomPercent}
            pageWidth={enginePage.width}
            pageHeight={enginePage.height}
            isCurrent
          />
        </div>
      ) : (
        <div className="lf-viewer-canvas flex-grow-1 overflow-auto p-3">
          <div className="d-flex flex-row gap-3 align-items-start justify-content-center">
            <figure className="m-0 text-center">
              <figcaption className="small text-muted mb-1">Source (raster)</figcaption>
              <div
                className="lf-viewer-page-host"
                style={{ width: enginePage.width, height: enginePage.height, transform: `scale(${scale})` }}
              >
                {backgroundUrl ? (
                  <img
                    src={backgroundUrl}
                    alt={`Source raster of page ${currentPage}`}
                    style={{ width: "100%", height: "100%" }}
                    draggable={false}
                  />
                ) : (
                  <div className="lf-empty small text-muted">No raster for this page.</div>
                )}
              </div>
            </figure>
            <figure className="m-0 text-center">
              <figcaption className="small text-muted mb-1">Reconstruction (live)</figcaption>
              <ViewerPageHost
                engine={engine}
                pageNumber={currentPage}
                zoomPercent={zoomPercent}
                pageWidth={enginePage.width}
                pageHeight={enginePage.height}
                isCurrent={false}
              />
            </figure>
          </div>
        </div>
      )}
    </div>
  );
}
