import { RouterProvider } from "react-router-dom";

import { CommandProvider } from "../context/CommandContext";
import { DocumentManagerProvider } from "../context/DocumentManagerContext";
import { AppEventBusProvider } from "../context/EventBusContext";
import { ViewerEngineProvider } from "../context/ViewerEngineContext";
import { WorkspaceProvider } from "../context/WorkspaceContext";
import { WorkspaceServiceProvider } from "../context/WorkspaceServiceContext";
import { router } from "../routes/router";

/** All context providers sit ABOVE the router so their state (the
 * ViewerEngine singleton, the WorkspaceService, the Document Manager, the
 * command registry, the shared workspace state, the app event bus) survives
 * route changes — `RouterProvider` swaps out the routed element tree, but
 * everything wrapped around it here does not remount. Order matters:
 * WorkspaceServiceProvider needs the engine; WorkspaceProvider and
 * ViewerEngineProvider both need the event bus, so EventBus is outermost. */
export default function AppProviders() {
  return (
    <AppEventBusProvider>
      <CommandProvider>
        <ViewerEngineProvider>
          <WorkspaceServiceProvider>
            <DocumentManagerProvider>
              <WorkspaceProvider>
                <RouterProvider router={router} />
              </WorkspaceProvider>
            </DocumentManagerProvider>
          </WorkspaceServiceProvider>
        </ViewerEngineProvider>
      </CommandProvider>
    </AppEventBusProvider>
  );
}
