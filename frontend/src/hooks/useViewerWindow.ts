import { RefObject, useEffect } from "react";

import { ViewerEngine } from "../viewer/ViewerEngine";

/** How long after a programmatic jump scroll-driven promotion stays
 * suppressed. Programmatic jumps scroll the target host into view; without
 * this window the IntersectionObserver would see intermediate pages fly by
 * and fight the jump. */
const SCROLL_SUPPRESS_MS = 500;

/** Scroll-driven windowing: watches the page hosts inside the canvas with
 * an IntersectionObserver, promotes the most-visible page to the current
 * page (source "scroll", so the canvas never scroll-jumps under the user),
 * which in turn makes the engine slide the mounted window — continuous
 * scrolling through a 2,000-page document emerges from this loop while at
 * most MAX_MOUNTED_PAGES iframes exist.
 *
 * Hosts are discovered via their `data-lf-page-host` attribute; a
 * MutationObserver re-observes as the strip mounts/unmounts hosts. */
export function useViewerWindow(engine: ViewerEngine, containerRef: RefObject<HTMLElement>, enabled: boolean) {
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled) return;

    // Start suppressed: on attach (tab switch back to the Viewer, view-mode
    // change) the container renders at scrollTop 0 before the current page
    // is scrolled back into view — promoting during that window cascades
    // the anchor page downward and loses the operator's place.
    let suppressUntil = performance.now() + SCROLL_SUPPRESS_MS;
    const offPage = engine.bus.on("PageChanged", ({ source }) => {
      if (source === "program") suppressUntil = performance.now() + SCROLL_SUPPRESS_MS;
    });

    const visibility = new Map<number, number>();

    const promoteMostVisible = () => {
      if (performance.now() < suppressUntil) return;
      let bestPage = 0;
      let bestRatio = 0;
      for (const [page, ratio] of visibility) {
        if (ratio > bestRatio) {
          bestRatio = ratio;
          bestPage = page;
        }
      }
      if (bestPage > 0 && bestRatio > 0 && bestPage !== engine.navigation.currentPage) {
        engine.navigation.jumpTo(bestPage, "scroll");
      }
    };

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const page = Number((entry.target as HTMLElement).dataset.lfPageHost);
          if (!Number.isFinite(page) || page <= 0) continue;
          visibility.set(page, entry.isIntersecting ? entry.intersectionRatio : 0);
        }
        promoteMostVisible();
      },
      { root: container, threshold: [0, 0.25, 0.5, 0.75, 1] },
    );

    const observeAll = () => {
      container.querySelectorAll<HTMLElement>("[data-lf-page-host]").forEach((el) => io.observe(el));
    };
    observeAll();

    // Strip changes mount/unmount hosts — rebuild observations (disconnect
    // clears stale entries for unmounted pages along with their ratios).
    const mo = new MutationObserver(() => {
      io.disconnect();
      visibility.clear();
      observeAll();
    });
    mo.observe(container, { childList: true });

    return () => {
      offPage();
      io.disconnect();
      mo.disconnect();
    };
  }, [engine, containerRef, enabled]);
}
