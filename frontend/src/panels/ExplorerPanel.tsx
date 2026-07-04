import { useNavigate } from "react-router-dom";

import ProjectExplorer from "../components/ProjectExplorer";
import { useWorkspace } from "../context/WorkspaceContext";
import ProjectTree from "./ProjectTree";

/** Combines the project list/upload UI (reused unchanged from Phase 1) with
 * the IDE-style breakdown of whichever project is currently selected.
 * Selecting a project navigates to its workspace route — the URL, not local
 * state, is what "a project is open" means. */
export default function ExplorerPanel() {
  const { projects, isUploading, selectedProjectId, uploadFile, removeProject, selectProject } = useWorkspace();
  const navigate = useNavigate();

  const handleSelect = (projectId: string) => {
    selectProject(projectId);
    navigate(`/workspace/${projectId}`);
  };

  return (
    <div className="lf-explorer-panel d-flex flex-column h-100">
      <ProjectExplorer
        projects={projects}
        isUploading={isUploading}
        selectedProjectId={selectedProjectId}
        onUpload={uploadFile}
        onDelete={removeProject}
        onSelect={handleSelect}
      />
      {selectedProjectId && (
        <div className="lf-explorer-tree flex-grow-1 overflow-auto border-top">
          <ProjectTree projectId={selectedProjectId} />
        </div>
      )}
    </div>
  );
}
