import { AccuracySettings } from "./types";

const OVERLAY_LAYER_SELECTORS = [".lf-layer-images", ".lf-layer-shapes", ".lf-layer-text"];

/** Renders one generated page by loading its served HTML into a same-origin
 * <iframe>. This is the single rendering path for the whole app: the iframe
 * is a real document, so the browser resolves the page's relative asset
 * URLs, loads @font-face fonts at the (iframe) document level, and paints
 * exactly as if the file were opened directly — no CSS inlining, no URL
 * rewriting, and none of the Shadow-DOM @font-face quirks (where fonts
 * declared inside a shadow root never register in document.fonts, so a
 * font-load wait is impossible and text paints with fallback metrics).
 *
 * The iframe src points at the backend static mount via the app origin
 * (Vite proxies /static → backend), so it stays same-origin and
 * contentDocument is fully accessible for selection and layer toggling. */
export class IframeRenderer {
  private iframe: HTMLIFrameElement;

  constructor(host: HTMLElement) {
    this.iframe = document.createElement("iframe");
    this.iframe.setAttribute("scrolling", "no");
    this.iframe.setAttribute("title", "page");
    this.iframe.style.cssText = "border:0;width:100%;height:100%;display:block;background:#fff;";
    host.appendChild(this.iframe);
  }

  /** Resolves once the iframe document has loaded AND its fonts are ready,
   * so callers can reveal the page knowing the first paint uses the real
   * fonts (correct glyph metrics), not fallbacks. */
  async load(url: string): Promise<void> {
    await new Promise<void>((resolve, reject) => {
      const onLoad = () => resolve();
      const onError = () => reject(new Error(`iframe failed to load ${url}`));
      this.iframe.addEventListener("load", onLoad, { once: true });
      this.iframe.addEventListener("error", onError, { once: true });
      this.iframe.src = url;
    });

    const doc = this.iframe.contentDocument;
    if (doc?.fonts) {
      try {
        await doc.fonts.ready;
      } catch {
        // font readiness is best-effort; never block rendering on it
      }
    }
  }

  get root(): Document | null {
    return this.iframe.contentDocument;
  }

  /** Accuracy Debug View: isolate the rendered background raster from the
   * extracted text/image overlay by toggling layer visibility/opacity
   * directly in the iframe document. */
  applyAccuracySettings(settings: AccuracySettings): void {
    const doc = this.iframe.contentDocument;
    if (!doc) return;

    const background = doc.querySelector<HTMLElement>(".lf-layer-background");
    if (background) {
      background.style.display = settings.mode === "overlay-only" ? "none" : "";
    }

    const overlayOpacity = settings.mode === "combined" ? settings.overlayOpacity / 100 : 1;
    for (const selector of OVERLAY_LAYER_SELECTORS) {
      const layer = doc.querySelector<HTMLElement>(selector);
      if (!layer) continue;
      layer.style.display = settings.mode === "background-only" ? "none" : "";
      layer.style.opacity = String(overlayOpacity);
    }
  }

  clear(): void {
    this.iframe.remove();
  }
}
