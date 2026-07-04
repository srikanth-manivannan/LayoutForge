/** Pure windowing math: which page numbers should exist in the DOM. For a
 * 2,000-page document, only a small contiguous window around the anchor is
 * ever mounted — never the whole document. */
export class Viewport {
  constructor(private radius: number = 1) {}

  /** A contiguous window of up to `count` pages centered on `anchor`,
   * clamped to [1, pageCount]. When the anchor sits near an edge the window
   * shifts inward so it keeps its full size where possible. */
  windowAround(anchor: number, count: number, pageCount: number): number[] {
    if (pageCount <= 0) return [];
    const size = Math.min(Math.max(1, count), pageCount);
    let start = anchor - Math.floor(size / 2);
    start = Math.max(1, Math.min(start, pageCount - size + 1));
    const pages: number[] = [];
    for (let page = start; page < start + size; page++) pages.push(page);
    return pages;
  }

  /** The active mount window for an anchor page (current ± radius). */
  pagesToMount(currentPage: number, pageCount: number): number[] {
    return this.windowAround(currentPage, this.radius * 2 + 1, pageCount);
  }
}
