import { createContext, ReactNode, useContext, useRef } from "react";

import { WorkspaceService } from "../workspace/WorkspaceService";
import { useViewerEngine } from "./ViewerEngineContext";

const WorkspaceServiceCtx = createContext<WorkspaceService | null>(null);

/** One WorkspaceService per app, wrapping the single ViewerEngine singleton —
 * same stable-across-routes requirement as the engine itself. */
export function WorkspaceServiceProvider({ children }: { children: ReactNode }) {
  const engine = useViewerEngine();
  const serviceRef = useRef<WorkspaceService | null>(null);
  if (!serviceRef.current) serviceRef.current = new WorkspaceService(engine);

  return <WorkspaceServiceCtx.Provider value={serviceRef.current}>{children}</WorkspaceServiceCtx.Provider>;
}

export function useWorkspaceService(): WorkspaceService {
  const service = useContext(WorkspaceServiceCtx);
  if (!service) throw new Error("useWorkspaceService must be used within WorkspaceServiceProvider");
  return service;
}
