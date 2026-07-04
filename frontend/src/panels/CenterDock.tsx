import { ReactNode, useEffect, useRef } from "react";

import { WorkspacePanelDescriptor } from "../workspace/WorkspacePanel";

export type CenterPanelKey = "viewer" | "compare" | "validation";

type CenterPanel = WorkspacePanelDescriptor & { id: CenterPanelKey };

const PANELS: CenterPanel[] = [
  { id: "viewer", title: "Viewer" },
  { id: "compare", title: "Compare" },
  { id: "validation", title: "Validation" },
];

interface CenterDockProps {
  active: CenterPanelKey;
  onChange: (key: CenterPanelKey) => void;
  viewer: ReactNode;
  compare: ReactNode;
  validation: ReactNode;
}

/** The center dock's own tab strip — the one dock in the workspace where
 * panels are actually switched (mutually exclusive), so it's where the
 * WorkspacePanel lifecycle contract's activate/deactivate calls are real
 * rather than trivial. These tabs are the Workspace Modes of the approved
 * product design (docs/design/04_NAVIGATION.md): switching changes the
 * center surface only, and page/zoom/selection carry across. */
export default function CenterDock({ active, onChange, viewer, compare, validation }: CenterDockProps) {
  const previousActive = useRef<CenterPanelKey | null>(null);

  useEffect(() => {
    if (previousActive.current && previousActive.current !== active) {
      PANELS.find((p) => p.id === previousActive.current)?.deactivate?.();
    }
    PANELS.find((p) => p.id === active)?.activate?.();
    previousActive.current = active;
  }, [active]);

  return (
    <div className="lf-center-dock d-flex flex-column h-100">
      <div className="lf-tab-strip">
        {PANELS.map((panel) => (
          <button
            key={panel.id}
            type="button"
            className={`lf-tab${active === panel.id ? " active" : ""}`}
            onClick={() => onChange(panel.id)}
          >
            {panel.title}
          </button>
        ))}
      </div>
      <div className="lf-center-dock-content flex-grow-1 overflow-hidden">
        {active === "viewer" && viewer}
        {active === "compare" && compare}
        {active === "validation" && validation}
      </div>
    </div>
  );
}
