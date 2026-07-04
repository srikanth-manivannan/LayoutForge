import { useEffect, useState } from "react";

import { DiagnosticsSnapshot } from "../viewer/types";
import { ViewerEngine } from "../viewer/ViewerEngine";
import { WorkspacePanelDescriptor } from "../workspace/WorkspacePanel";

interface DevDiagnosticsPanelProps {
  engine: ViewerEngine;
  zoomPercent: number;
}

/** Developer-only diagnostics (Ctrl+Shift+D) — the 2C successor of the
 * stabilization-phase ViewerDebugPanel, now hidden by default instead of a
 * visible toolbar toggle: viewer state machine, mounted-window contents
 * (the MAX_MOUNTED_PAGES cap made observable), zoom, missing assets, last
 * error. Satisfies the WorkspacePanelDescriptor contract trivially via its
 * own mount/unmount. */
export const devDiagnosticsDescriptor: WorkspacePanelDescriptor = {
  id: "dev-diagnostics",
  title: "Page Cache / Diagnostics",
};

export default function DevDiagnosticsPanel({ engine, zoomPercent }: DevDiagnosticsPanelProps) {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsSnapshot>(engine.getDiagnostics());

  useEffect(() => engine.bus.on("DiagnosticsChanged", setDiagnostics), [engine]);

  return (
    <div
      className="small p-2 border-top"
      style={{
        fontFamily: "var(--lf-font-mono)",
        fontSize: "var(--lf-fs-xs)",
        background: "var(--lf-bg-sunken)",
        color: "var(--lf-text-muted)",
      }}
    >
      <strong style={{ color: "var(--lf-text)" }}>Diagnostics</strong> (Ctrl+Shift+D)
      <span className="ms-3">state: {diagnostics.state}</span>
      <span className="ms-3">current: {engine.navigation.currentPage}</span>
      <span className="ms-3">mounted [{diagnostics.mountedPages.join(", ")}]</span>
      <span className="ms-3">zoom: {Math.round(zoomPercent)}%</span>
      <span className="ms-3">view: {engine.currentViewMode}</span>
      <span className="ms-3">
        missing assets: {diagnostics.missingAssets.length === 0 ? "none" : diagnostics.missingAssets.length}
      </span>
      <span className="ms-3">last error: {diagnostics.lastError ?? "none"}</span>
    </div>
  );
}
