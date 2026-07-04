import { useNavigate } from "react-router-dom";

import { useWorkspace } from "../context/WorkspaceContext";

const STATUS_BADGE: Record<string, string> = {
  created: "text-bg-secondary",
  processing: "text-bg-primary",
  ready: "text-bg-success",
  failed: "text-bg-danger",
};

/** Full-page project listing (as opposed to the compact list in the
 * Explorer panel) — every project, sortable by recency, with a delete
 * action. Reuses `useWorkspace` directly rather than duplicating its state. */
export default function ProjectsPage() {
  const { projects, removeProject, selectProject } = useWorkspace();
  const navigate = useNavigate();

  const openProject = (projectId: string) => {
    selectProject(projectId);
    navigate(`/workspace/${projectId}`);
  };

  return (
    <div className="p-4">
      <h5 className="mb-3">Projects</h5>
      {projects.length === 0 ? (
        <p className="text-muted">No projects yet. Upload a PDF from the Dashboard to get started.</p>
      ) : (
        <table className="table table-sm align-middle">
          <thead>
            <tr>
              <th>Name</th>
              <th>Pages</th>
              <th>Status</th>
              <th>Updated</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr key={project.id} role="button" onClick={() => openProject(project.id)}>
                <td className="fw-semibold">{project.name}</td>
                <td>{project.page_count}</td>
                <td>
                  <span className={`badge ${STATUS_BADGE[project.status] ?? "text-bg-secondary"}`}>{project.status}</span>
                </td>
                <td className="text-muted small">{new Date(project.updated_at).toLocaleString()}</td>
                <td className="text-end">
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger"
                    onClick={(event) => {
                      event.stopPropagation();
                      removeProject(project.id);
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
