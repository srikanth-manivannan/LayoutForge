import { UIEvent, useCallback, useEffect, useRef, useState } from "react";

import { PageRead } from "../api/client";

/** Fixed geometry keeps the virtualization math exact regardless of page
 * aspect ratio (the <img> letterboxes inside via object-fit). */
const ROW_HEIGHT = 108;
const OVERSCAN = 5;

interface ThumbnailRailProps {
  pages: PageRead[];
  currentPage: number;
  resolveUrl: (path: string | null) => string | null;
  onSelect: (pageNumber: number) => void;
}

/** Windowed page thumbnails — the same windowing philosophy as the viewer
 * applied to plain `<img loading="lazy">` elements (never iframes): only
 * rows near the scroll viewport exist in the DOM, so a 2,000-page document
 * costs a few dozen nodes, not thousands. Thumbnails reuse the page
 * background rasters the pipeline already produces; no backend involved. */
export default function ThumbnailRail({ pages, currentPage, resolveUrl, onSelect }: ThumbnailRailProps) {
  const railRef = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState<[number, number]>([0, 0]);

  const computeRange = useCallback(() => {
    const rail = railRef.current;
    if (!rail) return;
    const first = Math.max(0, Math.floor(rail.scrollTop / ROW_HEIGHT) - OVERSCAN);
    const visible = Math.ceil(rail.clientHeight / ROW_HEIGHT);
    const last = Math.min(pages.length, first + visible + OVERSCAN * 2);
    setRange(([prevFirst, prevLast]) => (prevFirst === first && prevLast === last ? [prevFirst, prevLast] : [first, last]));
  }, [pages.length]);

  useEffect(() => {
    computeRange();
  }, [computeRange]);

  // Keep the current page's thumbnail in view when navigation happens
  // elsewhere (buttons, canvas scroll, go-to-page).
  useEffect(() => {
    const rail = railRef.current;
    if (!rail) return;
    const top = (currentPage - 1) * ROW_HEIGHT;
    if (top < rail.scrollTop || top + ROW_HEIGHT > rail.scrollTop + rail.clientHeight) {
      rail.scrollTo({ top: top - rail.clientHeight / 2 + ROW_HEIGHT / 2 });
    }
  }, [currentPage]);

  const handleScroll = (_event: UIEvent<HTMLDivElement>) => computeRange();

  const [first, last] = range;

  return (
    <div
      ref={railRef}
      className="lf-thumb-rail"
      onScroll={handleScroll}
      role="listbox"
      aria-label="Page thumbnails"
    >
      <div style={{ height: pages.length * ROW_HEIGHT, position: "relative" }}>
        {pages.slice(first, last).map((page, offset) => {
          const index = first + offset;
          const url = resolveUrl(page.background_image);
          const isCurrent = page.page_number === currentPage;
          return (
            <button
              key={page.page_number}
              type="button"
              role="option"
              aria-selected={isCurrent}
              className={`lf-thumb${isCurrent ? " lf-thumb-current" : ""}`}
              style={{ top: index * ROW_HEIGHT }}
              onClick={() => onSelect(page.page_number)}
              title={`Page ${page.page_number}`}
            >
              {url ? (
                <img src={url} alt="" loading="lazy" draggable={false} />
              ) : (
                <span className="lf-thumb-blank" aria-hidden="true" />
              )}
              <span className="lf-thumb-num">{page.page_number}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
