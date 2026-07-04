import { setTheme, Theme, toggleTheme } from "../theme/theme";
import { Command } from "./types";

/** Today's commands wrap existing ViewerEngine calls. `view.*`/`export.*`/
 * `validate.*` are registered now but disabled (`enabled: () => false`) so
 * they show up in the registry/future palette as known, discoverable
 * capabilities without pretending to work before 2B/2C/Phase 4 implement them. */
export function createBuiltinCommands(): Command[] {
  return [
    { id: "navigate.first", title: "First Page", group: "navigate", keybinding: "Home", run: (ctx) => ctx.workspace.navigateFirst() },
    {
      id: "navigate.previous",
      title: "Previous Page",
      group: "navigate",
      keybinding: "PageUp",
      run: (ctx) => ctx.workspace.navigatePrevious(),
    },
    { id: "navigate.next", title: "Next Page", group: "navigate", keybinding: "PageDown", run: (ctx) => ctx.workspace.navigateNext() },
    { id: "navigate.last", title: "Last Page", group: "navigate", keybinding: "End", run: (ctx) => ctx.workspace.navigateLast() },
    { id: "navigate.jumpTo", title: "Jump to Page", group: "navigate", run: (ctx) => {
      const page = ctx.args?.page;
      if (typeof page === "number") ctx.workspace.navigateTo(page);
    } },
    {
      id: "zoom.setPercent",
      title: "Set Zoom",
      group: "zoom",
      run: (ctx) => {
        const percent = ctx.args?.percent;
        if (typeof percent === "number") ctx.workspace.setZoomPercent(percent);
      },
    },
    {
      id: "zoom.fitWidth",
      title: "Fit Width",
      group: "zoom",
      run: (ctx) => {
        const { width, height } = (ctx.args ?? {}) as { width?: number; height?: number };
        if (typeof width === "number" && typeof height === "number") {
          ctx.workspace.setZoomFit("fit-width", width, height);
        }
      },
    },
    // Theme — app-level, works everywhere (Settings, future palette/keybinding).
    {
      id: "view.setTheme",
      title: "Set Theme",
      group: "view",
      run: (ctx) => {
        const theme = ctx.args?.theme;
        if (theme === "light" || theme === "dark") setTheme(theme as Theme);
      },
    },
    { id: "view.toggleTheme", title: "Toggle Light/Dark Theme", group: "view", run: () => toggleTheme() },
    {
      id: "view.setMode",
      title: "Set View Mode",
      group: "view",
      run: (ctx) => {
        const mode = ctx.args?.mode;
        if (mode === "continuous" || mode === "single" || mode === "facing" || mode === "book") {
          ctx.workspace.setViewMode(mode);
        }
      },
    },
    { id: "zoom.in", title: "Zoom In", group: "zoom", keybinding: "Ctrl+=", run: (ctx) => ctx.workspace.zoomIn() },
    { id: "zoom.out", title: "Zoom Out", group: "zoom", keybinding: "Ctrl+-", run: (ctx) => ctx.workspace.zoomOut() },
    // Reserved — rotate needs Selection-safe box swaps; later 2B increment.
    { id: "view.rotate", title: "Rotate Page", group: "view", enabled: () => false, run: () => undefined },
    { id: "validate.run", title: "Run Validation", group: "validate", run: (ctx) => ctx.bus.emit("validation:run", {}) },
    // Reserved — implemented in Phase 4 (EPUB Production Platform) via plugins/exporters.
    { id: "export.html", title: "Export HTML", group: "export", enabled: () => false, run: () => undefined },
    { id: "export.epub", title: "Export EPUB", group: "export", enabled: () => false, run: () => undefined },
  ];
}
