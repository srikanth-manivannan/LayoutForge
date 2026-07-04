import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listPages, ProjectRead } from "../api/client";
import { Badge, BadgeStatus, Button, Progress } from "../components/ui";
import { useWorkspace } from "../context/WorkspaceContext";

const STATIC_ROOT = "/static/projects";
const RECENT_LIMIT = 8;

function statusOf(project: ProjectRead): BadgeStatus {
  if (project.status === "ready") return "ready";
  if (project.status === "failed") return "failed";
  return "processing";
}

function StatTile({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="lf-stat-card">
      <div className="lf-stat-value" style={tone ? { color: tone } : undefined}>
        {value}
      </div>
      <div className="lf-stat-label">{label}</div>
    </div>
  );
}

/** The launcher (approved product principle: Dashboard is where you pick
 * the next title, not part of the production loop). Answers "what's in
 * flight, what's ready, what failed" in seconds: whole-area drop target,
 * live conversion card, exact production counts, and recent projects as
 * cards with real page-1 thumbnails (the page background rasters the
 * pipeline already produced — fetched lazily, one small /pages read per
 * visible card, cached for the session). */
export default function DashboardPage() {
  const { projects, activeJob, isUploading, uploadFile, selectProject } = useWorkspace();
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [thumbs, setThumbs] = useState<Record<string, string | null>>({});

  const recentProjects = [...projects]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, RECENT_LIMIT);

  useEffect(() => {
    let cancelled = false;
    for (const project of recentProjects) {
      if (project.status !== "ready" || thumbs[project.id] !== undefined) continue;
      listPages(project.id)
        .then((pages) => {
          if (cancelled) return;
          const first = pages.find((page) => page.background_image);
          setThumbs((prev) => ({
            ...prev,
            [project.id]: first?.background_image ? `${STATIC_ROOT}/${project.id}/${first.background_image}` : null,
          }));
        })
        .catch(() => {
          if (!cancelled) setThumbs((prev) => ({ ...prev, [project.id]: null }));
        });
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projects]);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(false);
      const file = event.dataTransfer.files?.[0];
      if (file) uploadFile(file);
    },
    [uploadFile],
  );

  const openProject = (projectId: string) => {
    selectProject(projectId);
    navigate(`/workspace/${projectId}`);
  };

  const totalPages = projects.reduce((sum, p) => sum + p.page_count, 0);
  const readyCount = projects.filter((p) => p.status === "ready").length;
  const processingCount = projects.filter((p) => p.status === "processing" || p.status === "created").length;
  const failedCount = projects.filter((p) => p.status === "failed").length;

  return (
    <div
      className="lf-dashboard p-4"
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <div className="d-flex align-items-baseline gap-3 mb-3">
        <h5 className="mb-0">LayoutForge Studio</h5>
        <span className="text-muted small">
          {readyCount} ready for proofing{processingCount > 0 ? ` · ${processingCount} converting` : ""}
          {failedCount > 0 ? ` · ${failedCount} failed` : ""}
        </span>
      </div>

      <div className={`lf-dropzone mb-4${isDragging ? " dragging" : ""}`}>
        <div className="fw-semibold mb-1">{isUploading ? "Uploading…" : "Drop a PDF anywhere to import"}</div>
        <div className="text-muted small mb-2">or</div>
        <label className="lfui-btn lfui-btn--primary mb-0" style={{ cursor: "pointer" }}>
          Import PDF
          <input
            type="file"
            accept="application/pdf"
            className="d-none"
            disabled={isUploading}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadFile(file);
              event.target.value = "";
            }}
          />
        </label>
      </div>

      <div className="row g-4 mb-4">
        <div className="col-lg-7">
          <h6 className="text-uppercase text-muted small mb-2">Active conversion</h6>
          {activeJob && activeJob.status !== "completed" ? (
            <div className="lf-card-panel p-3">
              <div className="d-flex align-items-center gap-2 mb-2 small">
                <Badge status={activeJob.status === "failed" ? "failed" : "processing"}>{activeJob.status}</Badge>
                {activeJob.stage && <span className="text-muted">stage: {activeJob.stage}</span>}
                <span className="ms-auto text-muted">{activeJob.progress}%</span>
              </div>
              <Progress aria-label="Conversion progress" percent={activeJob.progress} />
              {activeJob.error_message && <div className="small text-danger mt-2">{activeJob.error_message}</div>}
            </div>
          ) : (
            <p className="text-muted small mb-0">No conversion in flight.</p>
          )}
        </div>
        <div className="col-lg-5">
          <h6 className="text-uppercase text-muted small mb-2">Production summary</h6>
          <div className="lf-stat-grid">
            <StatTile label="Ready" value={readyCount} tone="var(--lf-success)" />
            <StatTile label="Processing" value={processingCount} tone="var(--lf-accent)" />
            <StatTile label="Failed" value={failedCount} tone={failedCount ? "var(--lf-danger)" : undefined} />
            <StatTile label="Pages" value={totalPages} />
          </div>
        </div>
      </div>

      <h6 className="text-uppercase text-muted small mb-2">Recent projects</h6>
      {recentProjects.length === 0 ? (
        <p className="text-muted small">No projects yet — import a PDF to create the first one.</p>
      ) : (
        <div className="lf-project-grid">
          {recentProjects.map((project) => {
            const thumb = thumbs[project.id];
            return (
              <div key={project.id} className="lf-project-card" role="button" onClick={() => openProject(project.id)}>
                <div className="lf-project-thumb">
                  {thumb ? (
                    <img src={thumb} alt="" loading="lazy" draggable={false} />
                  ) : (
                    <span className="lf-project-thumb-blank" aria-hidden="true" />
                  )}
                </div>
                <div className="p-2 d-flex flex-column gap-1">
                  <span className="fw-semibold small text-truncate" title={project.name}>
                    {project.name}
                  </span>
                  <span className="d-flex align-items-center gap-2 small text-muted">
                    {project.page_count} pages
                    <Badge status={statusOf(project)} className="ms-auto">
                      {project.status}
                    </Badge>
                  </span>
                  <Button
                    size="sm"
                    variant={project.status === "ready" ? "primary" : "secondary"}
                    onClick={(event) => {
                      event.stopPropagation();
                      openProject(project.id);
                    }}
                  >
                    {project.status === "ready" ? "Open" : project.status === "failed" ? "Details" : "Monitor"}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
