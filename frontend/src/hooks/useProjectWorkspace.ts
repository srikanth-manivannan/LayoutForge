import { useCallback, useEffect, useRef, useState } from "react";

import {
  deleteProject,
  getJob,
  JobRead,
  listPages,
  listProjects,
  PageRead,
  ProjectRead,
  uploadProject,
} from "../api/client";
import { PreviewError, withPreviewErrorHandling } from "../environment/PreviewError";

const POLL_INTERVAL_MS = 800;

export function useProjectWorkspace() {
  const [projects, setProjects] = useState<ProjectRead[]>([]);
  const [activeJob, setActiveJob] = useState<JobRead | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [pages, setPages] = useState<PageRead[]>([]);
  const [pagesError, setPagesError] = useState<PreviewError | null>(null);
  const lastStageRef = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setProjects(await listProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects.");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const loadPages = useCallback(async (projectId: string) => {
    const { data, error: previewError } = await withPreviewErrorHandling(
      `/api/projects/${projectId}/pages`,
      () => listPages(projectId),
    );
    if (previewError) {
      setPagesError(previewError);
      setPages([]);
    } else {
      setPagesError(null);
      setPages(data ?? []);
    }
  }, []);

  const selectProject = useCallback(
    (projectId: string) => {
      setSelectedProjectId(projectId);
      loadPages(projectId);
    },
    [loadPages],
  );

  useEffect(() => {
    if (!activeJob || activeJob.status === "completed" || activeJob.status === "failed") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const job = await getJob(activeJob.id);
        setActiveJob(job);
        if (job.stage && job.stage !== lastStageRef.current) {
          lastStageRef.current = job.stage;
          setLogLines((lines) => [...lines, `[${job.progress}%] stage: ${job.stage}`]);
        }
        if (job.status === "completed") {
          setLogLines((lines) => [...lines, "Job completed."]);
          refresh();
          if (job.project_id === selectedProjectId) loadPages(job.project_id);
        } else if (job.status === "failed") {
          setLogLines((lines) => [...lines, `Job failed: ${job.error_message ?? "unknown error"}`]);
          refresh();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to poll job status.");
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [activeJob, refresh, selectedProjectId, loadPages]);

  const uploadFile = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setError(null);
      setLogLines([`Uploading ${file.name}…`]);
      lastStageRef.current = null;
      try {
        const { project_id, job_id } = await uploadProject(file);
        setLogLines((lines) => [...lines, `Project ${project_id} created, job ${job_id} queued.`]);
        setActiveJob({
          id: job_id,
          project_id,
          status: "queued",
          stage: null,
          progress: 0,
          current_page: 0,
          total_pages: 0,
          started_at: null,
          finished_at: null,
          error_message: null,
        });
        await refresh();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Upload failed.";
        setError(message);
        setLogLines((lines) => [...lines, `Upload failed: ${message}`]);
      } finally {
        setIsUploading(false);
      }
    },
    [refresh],
  );

  const removeProject = useCallback(
    async (projectId: string) => {
      await deleteProject(projectId);
      if (projectId === selectedProjectId) {
        setSelectedProjectId(null);
        setPages([]);
        setPagesError(null);
      }
      await refresh();
    },
    [refresh, selectedProjectId],
  );

  return {
    projects,
    activeJob,
    logLines,
    isUploading,
    error,
    selectedProjectId,
    pages,
    pagesError,
    uploadFile,
    removeProject,
    selectProject,
  };
}
