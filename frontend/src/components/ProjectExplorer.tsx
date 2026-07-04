import { useRef } from "react";

import { ProjectRead } from "../api/client";

interface ProjectExplorerProps {
  projects: ProjectRead[];
  isUploading: boolean;
  selectedProjectId: string | null;
  onUpload: (file: File) => void;
  onDelete: (projectId: string) => void;
  onSelect: (projectId: string) => void;
}

const STATUS_BADGE: Record<ProjectRead["status"], string> = {
  created: "text-bg-secondary",
  processing: "text-bg-primary",
  ready: "text-bg-success",
  failed: "text-bg-danger",
};

export default function ProjectExplorer({
  projects,
  isUploading,
  selectedProjectId,
  onUpload,
  onDelete,
  onSelect,
}: ProjectExplorerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) onUpload(file);
    event.target.value = "";
  };

  return (
    <aside className="lf-panel lf-surface p-3">
      <div className="d-flex align-items-center justify-content-between mb-2">
        <h6 className="text-uppercase text-muted small mb-0">Projects</h6>
        <button
          type="button"
          className="btn btn-sm btn-primary"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
        >
          {isUploading ? "Uploading…" : "Upload PDF"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="d-none"
          onChange={handleFileChange}
        />
      </div>

      {projects.length === 0 && <p className="text-muted small">No projects yet. Upload a PDF to get started.</p>}

      <ul className="list-unstyled">
        {projects.map((project) => (
          <li
            key={project.id}
            role="button"
            onClick={() => onSelect(project.id)}
            className={`d-flex align-items-center justify-content-between py-1 border-bottom${
              project.id === selectedProjectId ? " bg-primary-subtle" : ""
            }`}
          >
            <div>
              <div className="small fw-semibold">{project.name}</div>
              <div className="small text-muted">{project.page_count} pages</div>
            </div>
            <div className="d-flex align-items-center gap-2">
              <span className={`badge ${STATUS_BADGE[project.status]}`}>{project.status}</span>
              <button
                type="button"
                className="btn btn-sm btn-outline-danger"
                aria-label={`Delete ${project.name}`}
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(project.id);
                }}
              >
                ×
              </button>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
