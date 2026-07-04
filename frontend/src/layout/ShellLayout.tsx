import { Outlet } from "react-router-dom";

import EnvironmentAlert from "../components/EnvironmentAlert";
import Toolbar from "../components/Toolbar";
import { useEnvironmentCheck } from "../environment/useEnvironmentCheck";
import NavRail from "./NavRail";

/** The outermost shell: Toolbar + environment alert (unchanged from Phase 1)
 * over a NavRail + routed content area. Everything below NavRail is owned
 * by the current route (Dashboard/Projects/Conversion/Settings/Workspace). */
export default function ShellLayout() {
  const { result: environment, isChecking, recheck } = useEnvironmentCheck();

  return (
    <div className="lf-shell">
      <Toolbar environment={environment} isChecking={isChecking} onRecheck={recheck} />
      <EnvironmentAlert environment={environment} />
      <div className="lf-shell-body">
        <NavRail />
        <div className="lf-shell-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
