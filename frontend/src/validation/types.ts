/** Validation engine types — shared between the Web Worker and the panel. */

export type FindingSeverity = "error" | "warning";
export type FindingCategory = "layout" | "text" | "fonts" | "assets";

export interface ValidationFinding {
  severity: FindingSeverity;
  category: FindingCategory;
  page: number;
  /** IDM object id when the finding points at one object; null for
   * page-level findings. */
  objectId: string | null;
  message: string;
}

export interface ValidationRun {
  findings: ValidationFinding[];
  pagesChecked: number;
  pageCount: number;
  finishedAt: number | null; // epoch ms; null while running
}

/** Worker protocol. */
export type WorkerRequest = { type: "run"; idmUrl: string };

export type WorkerResponse =
  | { type: "progress"; page: number; pageCount: number; findings: ValidationFinding[] }
  | { type: "done"; pageCount: number }
  | { type: "error"; message: string };
