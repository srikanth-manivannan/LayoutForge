import { NavLink, useParams, useSearchParams } from "react-router-dom";

const GLOBAL_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "◧" },
  { to: "/projects", label: "Projects", icon: "▤" },
  { to: "/conversion", label: "Conversion", icon: "⇄" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

const WORKSPACE_PANELS: { key: string; label: string; icon: string }[] = [
  { key: "viewer", label: "Viewer", icon: "▣" },
  { key: "compare", label: "Compare", icon: "◫" },
  { key: "validation", label: "Validation", icon: "✓" },
  { key: "logs", label: "Logs", icon: "≣" },
];

/** Left icon+label nav rail. The top group is global (always visible); the
 * context group only appears once a project is open (`:projectId` present in
 * the route) and links to `?panel=` on the workspace route — WorkspacePage
 * reads that query param as the single source of truth for which dockable
 * panel is active, so NavRail and the in-workspace tab strip never fall out
 * of sync.
 *
 * NavLink's built-in `isActive` only compares the pathname, not the query
 * string — every panel link shares the same `/workspace/:id` pathname, so
 * active-state for the context group is computed manually from `?panel=`. */
export default function NavRail() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const activePanel = searchParams.get("panel") ?? "viewer";

  return (
    <nav className="lf-nav-rail">
      <div className="lf-nav-group">
        {GLOBAL_ITEMS.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => `lf-nav-item${isActive ? " active" : ""}`}>
            <span className="lf-nav-icon" aria-hidden="true">
              {item.icon}
            </span>
            <span className="lf-nav-label">{item.label}</span>
          </NavLink>
        ))}
      </div>

      {projectId && (
        <div className="lf-nav-group lf-nav-group-context">
          <div className="lf-nav-section-title">Workspace</div>
          {WORKSPACE_PANELS.map((panel) => (
            <NavLink
              key={panel.key}
              to={`/workspace/${projectId}?panel=${panel.key}`}
              className={`lf-nav-item${activePanel === panel.key ? " active" : ""}`}
            >
              <span className="lf-nav-icon" aria-hidden="true">
                {panel.icon}
              </span>
              <span className="lf-nav-label">{panel.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </nav>
  );
}
