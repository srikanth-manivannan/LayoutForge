import { AppEvents } from "../context/EventBusContext";
import { EventBus } from "../viewer/EventBus";
import { WorkspaceService } from "../workspace/WorkspaceService";

/** Everything a command's `run`/`enabled` needs. UI controls never call the
 * ViewerEngine directly — they dispatch a command, which runs against the
 * WorkspaceService (never the engine itself), so the same seam can later
 * grow to power move/resize/delete/undo/redo and a command palette without
 * touching call sites or teaching the engine about projects. `args` carries
 * per-invocation parameters (e.g. a zoom percent) since commands are
 * otherwise argument-free. */
export interface CommandContext {
  workspace: WorkspaceService;
  navigate: (path: string) => void;
  /** App event bus — commands that trigger panel work (e.g. validate.run)
   * emit an event instead of holding a panel reference. */
  bus: EventBus<AppEvents>;
  args?: Record<string, unknown>;
}

export interface Command {
  id: string;
  title: string;
  group: string;
  run: (ctx: CommandContext) => void;
  /** Omitted (always enabled) unless a command needs to guard on state —
   * e.g. reserved commands that have no implementation yet. */
  enabled?: (ctx: CommandContext) => boolean;
  /** Reserved for the future command palette / keybinding system (Phase 2.5+). */
  keybinding?: string;
}
