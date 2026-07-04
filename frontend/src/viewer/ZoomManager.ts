import { EventBus } from "./EventBus";
import { ViewerEvents, ZoomState } from "./types";

export const ZOOM_PRESETS = [50, 75, 100, 125, 150, 200] as const;

/** The single place page scale is decided. Pages apply `transform: scale()`
 * driven by this manager rather than each component computing its own
 * zoom math. */
export class ZoomManager {
  private state: ZoomState = { mode: "fixed", percent: 100 };

  constructor(private bus: EventBus<ViewerEvents>) {}

  get current(): ZoomState {
    return this.state;
  }

  setFixed(percent: number): void {
    this.state = { mode: "fixed", percent };
    this.bus.emit("ZoomChanged", this.state);
  }

  /** Recomputes "fit-width"/"fit-page" against the current viewport/page
   * size. Call again whenever the container resizes. */
  setFit(mode: "fit-width" | "fit-page", viewportWidth: number, viewportHeight: number, pageWidth: number, pageHeight: number): void {
    const widthScale = viewportWidth / pageWidth;
    const percent =
      mode === "fit-width" ? widthScale * 100 : Math.min(widthScale, viewportHeight / pageHeight) * 100;
    this.state = { mode, percent: Math.max(10, percent) };
    this.bus.emit("ZoomChanged", this.state);
  }

  /** Steps to the next/previous preset relative to the current effective
   * percent (works from fit modes too — stepping converts to fixed). */
  zoomIn(): void {
    const next = ZOOM_PRESETS.find((preset) => preset > this.state.percent + 0.5);
    this.setFixed(next ?? ZOOM_PRESETS[ZOOM_PRESETS.length - 1]);
  }

  zoomOut(): void {
    const lower = [...ZOOM_PRESETS].reverse().find((preset) => preset < this.state.percent - 0.5);
    this.setFixed(lower ?? ZOOM_PRESETS[0]);
  }
}
