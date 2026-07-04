import { getProjectSummary, ProjectSummary } from "../api/client";
import { ValidationRun } from "../validation/types";
import { IdmDocument, IdmFont, IdmObject, IdmPage } from "./idmTypes";

const STATIC_ROOT = "/static/projects";
const MAX_CACHED_PROJECTS = 2;
const MAX_CACHED_SUMMARIES = 2;
const SEARCH_CHUNK_SIZE = 20; // pages indexed per background tick — keeps a 2,000-page search from blocking the UI

export interface SearchMatch {
  page: number;
  objectId: string;
  text: string;
}

/** The single frontend owner of a project's document data, and the
 * enforcement point for the Large Document memory rules: `idm.json` is
 * fetched lazily (only when something actually needs it) and cached behind
 * a small LRU cap — nothing else in the app should parse the whole IDM
 * itself. Every consumer (Properties, search, future validation) asks this
 * manager for just the page/object it needs.
 *
 * Honest scope note: `idm.json` is still fetched and parsed as one JSON
 * document per project (there is no backend support yet for fetching a
 * single page's slice without downloading the whole file) — the cap here
 * bounds how many *projects'* worth of that parsed data are held in memory
 * at once, and callers only ever read a page/object at a time from it. True
 * server-side partial/streaming IDM access is reserved for Phase 2.5. */
export class DocumentManager {
  private cache = new Map<string, IdmDocument>(); // insertion order == LRU order
  private inFlight = new Map<string, Promise<IdmDocument>>();
  private searchIndexes = new Map<string, SearchMatch[]>();

  // A `ProjectSummary` (statistics/manifest/health/warnings) is a different,
  // much smaller read than `idm.json` — it gets its own small cache so
  // consumers (e.g. the Explorer tree) never call the API client directly;
  // they ask the Document Manager, which stays the single owner of
  // everything known about a project's document.
  private summaryCache = new Map<string, ProjectSummary>();
  private summaryInFlight = new Map<string, Promise<ProjectSummary>>();

  async getDocument(projectId: string): Promise<IdmDocument> {
    const cached = this.cache.get(projectId);
    if (cached) {
      // Refresh LRU order.
      this.cache.delete(projectId);
      this.cache.set(projectId, cached);
      return cached;
    }

    const pending = this.inFlight.get(projectId);
    if (pending) return pending;

    const promise = fetch(`${STATIC_ROOT}/${projectId}/idm.json`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load idm.json for project ${projectId} (status ${response.status})`);
        }
        return response.json() as Promise<IdmDocument>;
      })
      .then((document) => {
        this.storeInCache(projectId, document);
        this.inFlight.delete(projectId);
        return document;
      })
      .catch((error) => {
        this.inFlight.delete(projectId);
        throw error;
      });

    this.inFlight.set(projectId, promise);
    return promise;
  }

  private storeInCache(projectId: string, document: IdmDocument): void {
    this.cache.set(projectId, document);
    while (this.cache.size > MAX_CACHED_PROJECTS) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey === undefined) break;
      this.cache.delete(oldestKey);
      this.searchIndexes.delete(oldestKey);
    }
  }

  async getPage(projectId: string, pageNumber: number): Promise<IdmPage | undefined> {
    const document = await this.getDocument(projectId);
    return document.pages.find((page) => page.number === pageNumber);
  }

  async getFont(projectId: string, fontId: string): Promise<IdmFont | undefined> {
    const document = await this.getDocument(projectId);
    return document.fonts.find((font) => font.id === fontId);
  }

  async getObject(projectId: string, objectId: string): Promise<IdmObject | undefined> {
    const document = await this.getDocument(projectId);
    for (const page of document.pages) {
      const text = page.text_blocks.find((block) => block.id === objectId);
      if (text) return { type: "text", page: page.number, element: text };
      const image = page.images.find((img) => img.id === objectId);
      if (image) return { type: "image", page: page.number, element: image };
      const shape = page.shapes.find((s) => s.id === objectId);
      if (shape) return { type: "shape", page: page.number, element: shape };
    }
    return undefined;
  }

  /** Builds (or reuses) a search index for the project in background chunks
   * so indexing a 2,000-page document never blocks a single frame, then
   * runs the query against it. `onProgress` (optional) is called after each
   * chunk with the matches found so far, so a search UI can show results
   * enriching progressively rather than waiting for the whole document. */
  async search(projectId: string, query: string, onProgress?: (matches: SearchMatch[]) => void): Promise<SearchMatch[]> {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return [];

    const document = await this.getDocument(projectId);
    const matches: SearchMatch[] = [];

    for (let start = 0; start < document.pages.length; start += SEARCH_CHUNK_SIZE) {
      const chunk = document.pages.slice(start, start + SEARCH_CHUNK_SIZE);
      for (const page of chunk) {
        for (const block of page.text_blocks) {
          if (block.text.toLowerCase().includes(normalizedQuery)) {
            matches.push({ page: page.number, objectId: block.id, text: block.text });
          }
        }
      }
      onProgress?.(matches);
      // Yield to the event loop between chunks so indexing large documents
      // never blocks scrolling/input.
      if (start + SEARCH_CHUNK_SIZE < document.pages.length) {
        await new Promise((resolve) => setTimeout(resolve, 0));
      }
    }

    this.searchIndexes.set(projectId, matches);
    return matches;
  }

  /** Fetches (or reuses the cached) `ProjectSummary` for a project —
   * statistics, manifest, health, warnings. `force` bypasses the cache, for
   * callers that know the underlying data just changed (e.g. after a
   * reconversion). */
  async getSummary(projectId: string, options?: { force?: boolean }): Promise<ProjectSummary> {
    if (!options?.force) {
      const cached = this.summaryCache.get(projectId);
      if (cached) {
        this.summaryCache.delete(projectId);
        this.summaryCache.set(projectId, cached);
        return cached;
      }
      const pending = this.summaryInFlight.get(projectId);
      if (pending) return pending;
    }

    const promise = getProjectSummary(projectId)
      .then((summary) => {
        this.summaryCache.set(projectId, summary);
        while (this.summaryCache.size > MAX_CACHED_SUMMARIES) {
          const oldestKey = this.summaryCache.keys().next().value;
          if (oldestKey === undefined) break;
          this.summaryCache.delete(oldestKey);
        }
        this.summaryInFlight.delete(projectId);
        return summary;
      })
      .catch((error) => {
        this.summaryInFlight.delete(projectId);
        throw error;
      });

    this.summaryInFlight.set(projectId, promise);
    return promise;
  }

  // Validation results live here (not in panel state) so tab switches and
  // remounts don't lose a completed run — the Document Manager owns
  // everything known about a project's document, findings included.
  private validationRuns = new Map<string, ValidationRun>();

  setValidationRun(projectId: string, run: ValidationRun): void {
    this.validationRuns.set(projectId, run);
  }

  getValidationRun(projectId: string): ValidationRun | undefined {
    return this.validationRuns.get(projectId);
  }

  invalidate(projectId: string): void {
    this.cache.delete(projectId);
    this.searchIndexes.delete(projectId);
    this.inFlight.delete(projectId);
    this.summaryCache.delete(projectId);
    this.summaryInFlight.delete(projectId);
    this.validationRuns.delete(projectId);
  }

  get cachedProjectIds(): string[] {
    return [...this.cache.keys()];
  }
}
