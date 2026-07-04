import { createBrowserRouter, Navigate } from "react-router-dom";

import ShellLayout from "../layout/ShellLayout";
import ConversionPage from "./ConversionPage";
import DashboardPage from "./DashboardPage";
import ProjectsPage from "./ProjectsPage";
import SettingsPage from "./SettingsPage";
import WorkspacePage from "./WorkspacePage";

/** Global routes (Dashboard/Projects/Conversion/Settings) plus the project
 * workspace route. Compare/Validation/Logs/Properties are NOT routes — they
 * are dockable panels/tabs inside `/workspace/:projectId` (see
 * docs/ARCHITECTURE.md, "Workspace Shell"). */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <ShellLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "projects", element: <ProjectsPage /> },
      { path: "conversion", element: <ConversionPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "workspace/:projectId", element: <WorkspacePage /> },
    ],
  },
]);
