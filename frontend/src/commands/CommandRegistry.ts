import { Command, CommandContext } from "./types";

/** The single place UI controls go through to act on the workspace. Buttons,
 * menus, the future command palette, and future keybindings all call
 * `execute(id, ctx)` — none of them import ViewerEngine methods or panel
 * internals directly. This indirection is what lets Phase 3 add editing
 * commands (move/resize/delete/undo/redo) without touching any existing
 * call site. */
export class CommandRegistry {
  private commands = new Map<string, Command>();

  register(command: Command): void {
    this.commands.set(command.id, command);
  }

  unregister(id: string): void {
    this.commands.delete(id);
  }

  get(id: string): Command | undefined {
    return this.commands.get(id);
  }

  list(group?: string): Command[] {
    const all = [...this.commands.values()];
    return group ? all.filter((command) => command.group === group) : all;
  }

  execute(id: string, ctx: CommandContext): void {
    const command = this.commands.get(id);
    if (!command) {
      // eslint-disable-next-line no-console
      console.warn(`[Command] Unknown command: ${id}`);
      return;
    }
    if (command.enabled && !command.enabled(ctx)) return;
    command.run(ctx);
  }
}
