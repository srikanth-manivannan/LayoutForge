import { useEffect, useRef } from "react";

import { ViewerEngine } from "../viewer/ViewerEngine";

interface ViewerPageHostProps {
  engine: ViewerEngine;
  pageNumber: number;
  zoomPercent: number;
  pageWidth: number;
  pageHeight: number;
  isCurrent: boolean;
}

export default function ViewerPageHost({
  engine,
  pageNumber,
  zoomPercent,
  pageWidth,
  pageHeight,
  isCurrent,
}: ViewerPageHostProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    engine.mountPage(pageNumber, host).catch((error: unknown) => {
      console.error(`Failed to mount page ${pageNumber}`, error);
    });
    return () => engine.unmountPage(pageNumber);
  }, [engine, pageNumber]);

  const scale = zoomPercent / 100;
  // Outer wrapper owns the SCALED layout size so neighbors (other pages,
  // split-view panes) lay out correctly at any zoom; the inner host keeps
  // the page's natural size and only transforms — the iframe inside is
  // never resized (golden-path rule).
  return (
    <div style={{ width: pageWidth * scale, height: pageHeight * scale, flex: "0 0 auto" }}>
      <div
        ref={hostRef}
        data-lf-page-host={pageNumber}
        className={`lf-viewer-page-host${isCurrent ? " lf-viewer-page-current" : ""}`}
        style={{ width: pageWidth, height: pageHeight, transform: `scale(${scale})`, transformOrigin: "top left" }}
      />
    </div>
  );
}
