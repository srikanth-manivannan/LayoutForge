import { EventBus } from "./EventBus";
import { SelectionInfo, ViewerEvents } from "./types";

/** Click-to-select inside one page's rendered document. Resolves a click to
 * the IDM object it came from via data-object-id — no DOM parsing needed by
 * whatever consumes SelectionChanged (a future editor included). Does not
 * implement drag/resize — there's no editing feature yet to attach it to. */
export class Selection {
  private detach: (() => void) | null = null;

  constructor(private bus: EventBus<ViewerEvents>) {}

  attach(root: (Document | ShadowRoot) | null, page: number): void {
    this.detach?.();
    if (!root) return;
    const handleClick = (event: Event) => {
      const target = event.target as Element | null;
      const element = target?.closest("[data-object-id]") as HTMLElement | null;
      if (!element) {
        this.bus.emit("SelectionChanged", null);
        return;
      }
      const info: SelectionInfo = {
        objectId: element.dataset.objectId ?? "",
        type: element.dataset.type ?? "unknown",
        page,
      };
      this.bus.emit("SelectionChanged", info);
    };
    root.addEventListener("click", handleClick);
    this.detach = () => root.removeEventListener("click", handleClick);
  }

  clear(): void {
    this.detach?.();
    this.detach = null;
  }
}
