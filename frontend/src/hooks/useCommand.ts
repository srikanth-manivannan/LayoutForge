import { useNavigate } from "react-router-dom";

import { useCommandRegistry } from "../context/CommandContext";
import { useAppEventBus } from "../context/EventBusContext";
import { useWorkspaceService } from "../context/WorkspaceServiceContext";

/** Convenience hook: returns a bound `execute(id, args?)` function so
 * components never have to assemble a CommandContext by hand. This is the
 * function every button/menu should call instead of reaching into the
 * WorkspaceService, ViewerEngine, or another panel directly. */
export function useCommand() {
  const registry = useCommandRegistry();
  const workspace = useWorkspaceService();
  const navigate = useNavigate();
  const bus = useAppEventBus();

  return (id: string, args?: Record<string, unknown>) => registry.execute(id, { workspace, navigate, bus, args });
}
