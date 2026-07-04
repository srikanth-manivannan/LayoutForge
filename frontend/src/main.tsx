import "bootstrap/dist/css/bootstrap.min.css";
import "./styles/tokens.css";
import "./styles/ui.css";
import "./styles/layout.css";
import "./styles/shell.css";
import "./styles/viewer.css";

import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { initTheme } from "./theme/theme";

// Apply the persisted theme before first paint so there is no light flash.
initTheme();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
