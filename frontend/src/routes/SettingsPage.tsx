import { useEffect, useState } from "react";

import { getVersion, VersionInfo } from "../api/client";
import { Button } from "../components/ui";
import { useCommand } from "../hooks/useCommand";
import { useTheme } from "../hooks/useTheme";

/** Only real, currently-meaningful information is shown here (theme,
 * backend version/build). Presets, keybindings, session restore, and
 * settings import/export are reserved for a later 2.x increment (see
 * docs/PHASE2_IMPLEMENTATION.md) and are intentionally not stubbed with
 * fake controls. */
export default function SettingsPage() {
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const theme = useTheme();
  const execute = useCommand();

  useEffect(() => {
    getVersion()
      .then(setVersion)
      .catch(() => setVersion(null));
  }, []);

  return (
    <div className="p-4">
      <h5 className="mb-3">Settings</h5>

      <h6 className="text-uppercase text-muted small mb-2">Appearance</h6>
      <div className="d-flex align-items-center gap-2 mb-1" role="radiogroup" aria-label="Theme">
        <Button
          variant={theme === "light" ? "primary" : "secondary"}
          role="radio"
          aria-checked={theme === "light"}
          onClick={() => execute("view.setTheme", { theme: "light" })}
        >
          Light
        </Button>
        <Button
          variant={theme === "dark" ? "primary" : "secondary"}
          role="radio"
          aria-checked={theme === "dark"}
          onClick={() => execute("view.setTheme", { theme: "dark" })}
        >
          Dark
        </Button>
      </div>
      <p className="text-muted small mb-4" style={{ maxWidth: 480 }}>
        Themes restyle the application only — the document preview always keeps its real colors,
        so proofing stays accurate.
      </p>

      <h6 className="text-uppercase text-muted small mb-2">About</h6>
      {version ? (
        <dl className="row small" style={{ maxWidth: 480 }}>
          <dt className="col-sm-4">Version</dt>
          <dd className="col-sm-8">{version.version}</dd>
          <dt className="col-sm-4">API Version</dt>
          <dd className="col-sm-8">{version.api_version}</dd>
          <dt className="col-sm-4">Build</dt>
          <dd className="col-sm-8">{version.build}</dd>
          {version.git_commit && (
            <>
              <dt className="col-sm-4">Commit</dt>
              <dd className="col-sm-8 text-truncate">{version.git_commit}</dd>
            </>
          )}
        </dl>
      ) : (
        <p className="text-muted small">Unable to load version information.</p>
      )}
      <p className="text-muted small mt-4">
        Presets, keybindings, session restore, and settings import/export are planned for a future increment.
      </p>
    </div>
  );
}
