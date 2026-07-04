import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import PreviewPane from "../components/PreviewPane";
import PropertiesPanel from "../components/PropertiesPanel";
import { useWorkspace } from "../context/WorkspaceContext";
import { useViewerEngine } from "../context/ViewerEngineContext";
import { useWorkspaceService } from "../context/WorkspaceServiceContext";
import ProductionWorkspaceLayout from "../layout/ProductionWorkspaceLayout";
import BottomDock from "../panels/BottomDock";
import CenterDock, { CenterPanelKey } from "../panels/CenterDock";
import ComparePanel from "../panels/ComparePanel";
import ExplorerPanel from "../panels/ExplorerPanel";
import ValidationPanel from "../panels/ValidationPanel";
import { ValidationFinding } from "../validation/types";
import { SelectionInfo } from "../viewer/types";

const VALID_PANELS: CenterPanelKey[] = ["viewer", "compare", "validation"];

/** The project workspace route (`/workspace/:projectId`). Compare,
 * Validation, Logs, and Properties are dockable panels/tabs *inside* this
 * one route — not separate destinations — matching how desktop publishing
 * software behaves. `?panel=` on the URL is the single source of truth for
 * which center-dock tab is active (kept in sync with NavRail's context
 * group). */
export default function WorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const { selectedProjectId, pages, pagesError, selectProject, projects, logLines, activeJob } = useWorkspace();
  const engine = useViewerEngine();
  const workspace = useWorkspaceService();
  const [selection, setSelection] = useState<SelectionInfo | null>(null);

  useEffect(() => engine.bus.on("SelectionChanged", setSelection), [engine]);

  useEffect(() => {
    if (projectId && projectId !== selectedProjectId) {
      selectProject(projectId);
    }
    // Unmount every iframe when leaving this route (going to another
    // section) so no page keeps rendering off-screen.
    return () => workspace.closeProject();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // The ROUTE owns opening the project in the WorkspaceService — not the
  // Viewer tab. Compare/Validation must work even when the workspace is
  // entered directly on their tab (?panel=…) with the Viewer never mounted.
  useEffect(() => {
    if (projectId && pages.length > 0 && !pagesError) {
      workspace.openProject(projectId, pages);
    }
  }, [projectId, pages, pagesError, workspace]);

  useEffect(() => {
    // A project id in the URL that no longer exists (e.g. deleted, or a
    // stale bookmark) — send the user back to Projects rather than showing
    // a blank workspace.
    if (projectId && projects.length > 0 && !projects.some((p) => p.id === projectId)) {
      navigate("/projects", { replace: true });
    }
  }, [projectId, projects, navigate]);

  if (!projectId) return null;

  const activePanel = (searchParams.get("panel") as CenterPanelKey) ?? "viewer";
  const centerPanel: CenterPanelKey = VALID_PANELS.includes(activePanel) ? activePanel : "viewer";

  const handleChangePanel = (panel: CenterPanelKey) => {
    setSearchParams({ panel }, { replace: true });
  };

  // Finding click-through (the inner loop's Validate→Fix leg): switch the
  // center surface back to the Viewer and drive the same navigation +
  // highlight pipeline search jumps use. highlightObject tolerates the
  // page not being mounted yet (applies on its PageRendered).
  const handleRevealFinding = useCallback(
    (finding: ValidationFinding) => {
      setSearchParams({ panel: "viewer" }, { replace: true });
      workspace.navigateTo(finding.page);
      if (finding.objectId) engine.highlightObject(finding.page, finding.objectId);
    },
    [engine, workspace, setSearchParams],
  );

  return (
    <ProductionWorkspaceLayout
      explorer={<ExplorerPanel />}
      center={
        <CenterDock
          active={centerPanel}
          onChange={handleChangePanel}
          viewer={
            <PreviewPane engine={engine} workspace={workspace} projectId={projectId} pages={pages} pagesError={pagesError} />
          }
          compare={<ComparePanel engine={engine} workspace={workspace} pages={pages} />}
          validation={<ValidationPanel projectId={projectId} workspace={workspace} onReveal={handleRevealFinding} />}
        />
      }
      properties={<PropertiesPanel selection={selection} projectId={projectId} />}
      renderBottomDock={({ collapsed, toggle, expand }) => (
        <BottomDock logLines={logLines} activeJob={activeJob} collapsed={collapsed} onToggle={toggle} onExpand={expand} />
      )}
    />
  );
}
