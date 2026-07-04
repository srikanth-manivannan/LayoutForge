import { createContext, ReactNode, useContext, useEffect, useRef } from "react";

import { ViewerEngine } from "../viewer/ViewerEngine";
import { useAppEventBus } from "./EventBusContext";

/** The ViewerEngine MUST be a stable singleton across route changes — a new
 * instance per render (or per route) would remount every iframe. Created
 * once via useRef, never replaced. */
const ViewerEngineCtx = createContext<ViewerEngine | null>(null);

export function ViewerEngineProvider({ children }: { children: ReactNode }) {
  const engineRef = useRef<ViewerEngine | null>(null);
  if (!engineRef.current) engineRef.current = new ViewerEngine();
  const engine = engineRef.current;

  const bus = useAppEventBus();
  useEffect(() => engine.bus.on("SelectionChanged", (selection) => bus.emit("selection:changed", selection)), [engine, bus]);

  return <ViewerEngineCtx.Provider value={engine}>{children}</ViewerEngineCtx.Provider>;
}

export function useViewerEngine(): ViewerEngine {
  const engine = useContext(ViewerEngineCtx);
  if (!engine) throw new Error("useViewerEngine must be used within ViewerEngineProvider");
  return engine;
}
