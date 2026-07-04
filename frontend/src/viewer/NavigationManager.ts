import { EventBus } from "./EventBus";
import { NavigationSource, ViewerEvents } from "./types";

/** Owns "what page are we on" — Next/Previous/Jump/First/Last — so
 * PreviewPane only needs to call these methods and react to PageChanged.
 * `source` distinguishes programmatic navigation (buttons/commands — the
 * canvas scrolls the page into view) from scroll-driven promotion (the
 * IntersectionObserver in useViewerWindow — the canvas must not scroll). */
export class NavigationManager {
  private current = 1;

  constructor(
    private bus: EventBus<ViewerEvents>,
    private pageCount: number,
  ) {}

  get currentPage(): number {
    return this.current;
  }

  setPageCount(pageCount: number): void {
    this.pageCount = pageCount;
  }

  jumpTo(page: number, source: NavigationSource = "program"): void {
    const clamped = Math.min(Math.max(1, page), Math.max(1, this.pageCount));
    if (clamped === this.current) return;
    this.current = clamped;
    this.bus.emit("PageChanged", { page: this.current, source });
  }

  next(): void {
    this.jumpTo(this.current + 1);
  }

  previous(): void {
    this.jumpTo(this.current - 1);
  }

  first(): void {
    this.jumpTo(1);
  }

  last(): void {
    this.jumpTo(this.pageCount);
  }
}
