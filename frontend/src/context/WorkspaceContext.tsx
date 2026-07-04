import { createContext, ReactNode, useCallback, useContext, useMemo } from "react";

import { useProjectWorkspace } from "../hooks/useProjectWorkspace";
import { useAppEventBus } from "./EventBusContext";

type WorkspaceContextValue = ReturnType<typeof useProjectWorkspace>;

const WorkspaceCtx = createContext<WorkspaceContextValue | null>(null);

/** Wraps the existing `useProjectWorkspace` hook in a single Provider so the
 * one polling loop it owns is shared across every route/panel instead of
 * being recreated (and re-polling) per consumer. Also re-broadcasts project
 * selection onto the app event bus, without changing the reusable hook
 * itself. */
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const workspace = useProjectWorkspace();
  const bus = useAppEventBus();

  const selectProject = useCallback(
    (projectId: string) => {
      workspace.selectProject(projectId);
      bus.emit("project:selected", { projectId });
    },
    [workspace, bus],
  );

  const value = useMemo(() => ({ ...workspace, selectProject }), [workspace, selectProject]);

  return <WorkspaceCtx.Provider value={value}>{children}</WorkspaceCtx.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceCtx);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
