import { ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { ImperativePanelHandle, Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

interface BottomDockState {
  collapsed: boolean;
  toggle: () => void;
  /** Expand if currently collapsed (used when the user clicks a tab). */
  expand: () => void;
}

interface ProductionWorkspaceLayoutProps {
  explorer: ReactNode;
  center: ReactNode;
  properties: ReactNode;
  renderBottomDock: (state: BottomDockState) => ReactNode;
}

/** Nested react-resizable-panels: an outer vertical group (main row over a
 * bottom dock) wrapping an inner horizontal group (Explorer | center |
 * Properties). Side panels are collapsible; every group persists its sizes
 * to localStorage via `autoSaveId` so a reload keeps the user's layout.
 *
 * The bottom dock DEFAULTS TO COLLAPSED (just its tab strip): the document
 * is the hero, and logs must not eat canvas height unless asked for
 * (Ctrl+J or clicking a tab). autoSaveId is versioned (-v2) so this new
 * default reaches layouts saved before the change. */
export default function ProductionWorkspaceLayout({
  explorer,
  center,
  properties,
  renderBottomDock,
}: ProductionWorkspaceLayoutProps) {
  const bottomRef = useRef<ImperativePanelHandle>(null);
  const [collapsed, setCollapsed] = useState(true);

  const expand = useCallback(() => {
    const panel = bottomRef.current;
    if (panel && panel.isCollapsed()) panel.resize(26);
  }, []);

  const toggle = useCallback(() => {
    const panel = bottomRef.current;
    if (!panel) return;
    if (panel.isCollapsed()) panel.resize(26);
    else panel.collapse();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey && event.key.toLowerCase() === "j") {
        event.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggle]);

  return (
    <PanelGroup direction="vertical" autoSaveId="lf-workspace-vertical-v2" className="lf-workspace-vertical">
      <Panel defaultSize={95} minSize={40} className="lf-workspace-main-row">
        <PanelGroup direction="horizontal" autoSaveId="lf-workspace-horizontal">
          <Panel defaultSize={18} minSize={12} collapsible className="lf-workspace-panel lf-workspace-explorer">
            {explorer}
          </Panel>
          <PanelResizeHandle className="lf-resize-handle lf-resize-handle-vertical" />
          <Panel defaultSize={60} minSize={30} className="lf-workspace-panel lf-workspace-center">
            {center}
          </Panel>
          <PanelResizeHandle className="lf-resize-handle lf-resize-handle-vertical" />
          <Panel defaultSize={22} minSize={14} collapsible className="lf-workspace-panel lf-workspace-properties">
            {properties}
          </Panel>
        </PanelGroup>
      </Panel>
      <PanelResizeHandle className="lf-resize-handle lf-resize-handle-horizontal" />
      <Panel
        ref={bottomRef}
        defaultSize={5}
        collapsedSize={5}
        collapsible
        minSize={12}
        onCollapse={() => setCollapsed(true)}
        onExpand={() => setCollapsed(false)}
        className="lf-workspace-panel lf-workspace-bottom-dock"
      >
        {renderBottomDock({ collapsed, toggle, expand })}
      </Panel>
    </PanelGroup>
  );
}
