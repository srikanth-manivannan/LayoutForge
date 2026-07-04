import { RefObject, useEffect } from "react";

import { WorkspaceService } from "../workspace/WorkspaceService";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    target.isContentEditable
  );
}

/** Viewer keyboard shortcuts (approved keyboard map, 04_NAVIGATION.md):
 * PageUp/PageDown/Home/End for navigation, Ctrl+= / Ctrl+- / Ctrl+0 for
 * zoom in / out / fit-width. Interim dispatcher until the command-palette /
 * keybinding system lands (the same bindings are declared as `keybinding`
 * on the corresponding commands so the two stay in sync). */
export function useViewerKeyboard(
  workspace: WorkspaceService,
  containerRef: RefObject<HTMLElement>,
  enabled: boolean,
  onFind?: () => void,
  onToggleDiagnostics?: () => void,
) {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (event: KeyboardEvent) => {
      // Ctrl+F opens document search even while an input is focused —
      // matching every desktop document tool.
      if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "f" && onFind) {
        event.preventDefault();
        onFind();
        return;
      }

      // Ctrl+Shift+D — developer diagnostics panel (2B/2C plan item).
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "d" && onToggleDiagnostics) {
        event.preventDefault();
        onToggleDiagnostics();
        return;
      }

      if (isEditableTarget(event.target)) return;

      if (!event.ctrlKey && !event.metaKey && !event.altKey) {
        switch (event.key) {
          case "PageDown":
            event.preventDefault();
            workspace.navigateNext();
            return;
          case "PageUp":
            event.preventDefault();
            workspace.navigatePrevious();
            return;
          case "Home":
            event.preventDefault();
            workspace.navigateFirst();
            return;
          case "End":
            event.preventDefault();
            workspace.navigateLast();
            return;
        }
        return;
      }

      if (event.ctrlKey && !event.altKey) {
        // "=" is the unshifted "+" key; browsers report either.
        if (event.key === "=" || event.key === "+") {
          event.preventDefault();
          workspace.zoomIn();
        } else if (event.key === "-") {
          event.preventDefault();
          workspace.zoomOut();
        } else if (event.key === "0") {
          const container = containerRef.current;
          if (container) {
            event.preventDefault();
            workspace.setZoomFit("fit-width", container.clientWidth, container.clientHeight);
          }
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [workspace, containerRef, enabled, onFind, onToggleDiagnostics]);
}
