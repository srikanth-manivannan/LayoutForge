export interface HealthResponse {
  status: string;
  app_env: string;
  storage_ok: boolean;
}

export interface VersionInfo {
  version: string;
  build: string;
  git_commit: string | null;
  api_version: number;
}

export interface ProjectRead {
  id: string;
  name: string;
  filename: string;
  page_count: number;
  status: "created" | "processing" | "ready" | "failed";
  created_at: string;
  updated_at: string;
}

export interface JobRead {
  id: string;
  project_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  stage: string | null;
  progress: number;
  current_page: number;
  total_pages: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface ProjectCreateResponse {
  project_id: string;
  job_id: string;
}

export interface PageRead {
  page_number: number;
  width: number;
  height: number;
  rotation: number;
  html_path: string | null;
  css_path: string | null;
  background_image: string | null;
}

export interface StatisticsRead {
  page_count: number;
  html_file_count: number;
  css_file_count: number;
  image_count: number;
  font_count: number;
  text_block_count: number;
  disk_size_bytes: number;
}

export interface ManifestPageRead {
  number: number;
  width: number;
  height: number;
  rotation: number;
  background_image: string | null;
}

export interface ManifestFontRead {
  id: string;
  family: string;
  weight: string;
  style: string;
  embedded: boolean;
}

export interface ManifestAssetRead {
  id: string;
  type: string;
  filename: string;
  path: string;
  referenced_pages: number[];
}

export interface ManifestRead {
  title: string | null;
  author: string | null;
  page_count: number;
  pages: ManifestPageRead[];
  fonts: ManifestFontRead[];
  assets: ManifestAssetRead[];
}

export interface HealthCheckRead {
  storage_ok: boolean;
  idm_ok: boolean;
  all_pages_rendered: boolean;
}

export interface ProgressRead {
  job_id: string;
  status: JobRead["status"];
  stage: string | null;
  progress: number;
  current_page: number;
  total_pages: number;
  error_message: string | null;
}

export interface ProjectSummary {
  project: ProjectRead;
  statistics: StatisticsRead;
  manifest: ManifestRead | null;
  health: HealthCheckRead;
  progress: ProgressRead | null;
  warnings: string[];
  recent_logs: string[];
}

export type LogStream = "application" | "conversion" | "performance";

export interface LogRead {
  stream: LogStream;
  lines: string[];
  truncated: boolean;
}

/** Carries the HTTP status alongside the message so callers can branch on
 * it (e.g. "404 on /pages" means something specific and actionable, not
 * just a generic failure). */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly url: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function asJson<T>(response: Response, url: string): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response body wasn't JSON; keep the generic message
    }
    throw new ApiError(detail, response.status, url);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return asJson(await fetch("/api/health"), "/api/health");
}

export async function getVersion(): Promise<VersionInfo> {
  return asJson(await fetch("/api/version"), "/api/version");
}

export async function listProjects(): Promise<ProjectRead[]> {
  return asJson(await fetch("/api/projects"), "/api/projects");
}

export async function uploadProject(file: File, name?: string): Promise<ProjectCreateResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);
  return asJson(await fetch("/api/projects", { method: "POST", body: formData }), "/api/projects");
}

export async function getJob(jobId: string): Promise<JobRead> {
  return asJson(await fetch(`/api/jobs/${jobId}`), `/api/jobs/${jobId}`);
}

export async function listPages(projectId: string): Promise<PageRead[]> {
  const url = `/api/projects/${projectId}/pages`;
  return asJson(await fetch(url), url);
}

export async function getProjectSummary(projectId: string): Promise<ProjectSummary> {
  const url = `/api/projects/${projectId}/summary`;
  return asJson(await fetch(url), url);
}

export async function getLogs(stream: LogStream = "application", tail = 200): Promise<LogRead> {
  const url = `/api/logs?stream=${stream}&tail=${tail}`;
  return asJson(await fetch(url), url);
}

export async function deleteProject(projectId: string): Promise<void> {
  const response = await fetch(`/api/projects/${projectId}`, { method: "DELETE" });
  if (!response.ok && response.status !== 404) {
    throw new ApiError(`Failed to delete project (status ${response.status})`, response.status, `/api/projects/${projectId}`);
  }
}
