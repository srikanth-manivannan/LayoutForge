import { createContext, ReactNode, useContext, useRef } from "react";

import { EventBus } from "../viewer/EventBus";
import { SelectionInfo } from "../viewer/types";

/** The app-wide promotion of the viewer's EventBus pattern: upload ->
 * pipeline-progress -> workspace -> viewer -> selection -> validation ->
 * properties -> plugins -> logs all communicate through this bus instead of
 * direct references, so future plugins/validators/exporters can subscribe
 * without touching existing call sites.
 *
 * Only a small set of events are actually emitted in sub-phase 2A
 * (project selection, and a re-broadcast of ViewerEngine's SelectionChanged
 * so panels that don't hold a ViewerEngine reference can still react to
 * selection). More producers (job progress, validation results) are added
 * as 2B/2C build the features that emit them. */
export interface AppEvents {
  "project:selected": { projectId: string };
  "selection:changed": SelectionInfo | null;
  /** Ask the Validation panel to start a run (emitted by `validate.run`). */
  "validation:run": Record<string, never>;
}

const EventBusContext = createContext<EventBus<AppEvents> | null>(null);

export function AppEventBusProvider({ children }: { children: ReactNode }) {
  const busRef = useRef<EventBus<AppEvents> | null>(null);
  if (!busRef.current) busRef.current = new EventBus<AppEvents>();
  return <EventBusContext.Provider value={busRef.current}>{children}</EventBusContext.Provider>;
}

export function useAppEventBus(): EventBus<AppEvents> {
  const bus = useContext(EventBusContext);
  if (!bus) throw new Error("useAppEventBus must be used within AppEventBusProvider");
  return bus;
}
