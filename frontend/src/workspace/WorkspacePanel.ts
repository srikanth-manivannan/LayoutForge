import { Command } from "../commands/types";

/** Contract every dockable workspace panel (Explorer, Viewer, Compare,
 * Validation, Properties, Logs, and future panels — e.g. 2B's Page Cache
 * Debug panel) should describe itself with, so the shell can register,
 * tab-switch, and tear panels down uniformly, and each panel can contribute
 * its own commands without the shell knowing its internals.
 *
 * Lifecycle hooks are all optional. Panels that are *switched* (today: the
 * CenterDock's Viewer/Compare/Validation tabs) get real activate/deactivate
 * calls when they become/stop being the visible tab. Panels that are
 * *always-on* docks (Explorer, Properties, the bottom Logs dock) never need
 * them — their own React mount/unmount already is their lifecycle, so they
 * satisfy this contract trivially without artificial boilerplate. */
export interface WorkspacePanelDescriptor {
  id: string;
  title: string;
  icon?: string;
  /** Called when the panel becomes the visible tab in its dock. */
  activate?: () => void;
  /** Called when another tab in the same dock becomes active, or the panel
   * is otherwise hidden without being torn down. */
  deactivate?: () => void;
  /** Called when the panel is torn down entirely (e.g. leaving the
   * workspace route). */
  dispose?: () => void;
  /** Commands this panel contributes to the registry; omitted if none. */
  commands?: () => Command[];
}
