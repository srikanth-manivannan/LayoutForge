import { getHealth, getVersion } from "../api/client";

/** Must match backend Settings.api_version (backend/app/core/config.py).
 * Bump this alongside that constant whenever a request/response shape
 * changes incompatibly. */
export const EXPECTED_API_VERSION = 1;

export interface EnvironmentCheckResult {
  backendReachable: boolean;
  apiVersionMatches: boolean;
  staticMountOk: boolean;
  storageOk: boolean;
  backendApiVersion: number | null;
  errors: string[];
}

async function checkStaticMount(): Promise<boolean> {
  try {
    const response = await fetch("/static/projects/.static_ok");
    if (!response.ok) return false;
    return (await response.text()).trim() === "ok";
  } catch {
    return false;
  }
}

/** Runs the full backend-environment check described in the stabilization
 * plan: backend reachable -> API version matches -> static mount works ->
 * storage directory accessible. Never throws — every failure is captured
 * in the result so the caller can show a meaningful message instead of a
 * silently empty preview. */
export async function checkEnvironment(): Promise<EnvironmentCheckResult> {
  const errors: string[] = [];
  let backendReachable = false;
  let storageOk = false;
  let apiVersionMatches = false;
  let backendApiVersion: number | null = null;

  try {
    const health = await getHealth();
    backendReachable = health.status === "ok";
    storageOk = health.storage_ok;
    if (!storageOk) errors.push("Backend reports storage is not accessible.");
  } catch (err) {
    errors.push(`Backend unreachable: ${err instanceof Error ? err.message : String(err)}`);
  }

  if (backendReachable) {
    try {
      const version = await getVersion();
      backendApiVersion = version.api_version;
      apiVersionMatches = version.api_version === EXPECTED_API_VERSION;
      if (!apiVersionMatches) {
        errors.push(
          `Backend API version mismatch: expected ${EXPECTED_API_VERSION}, got ${version.api_version}. ` +
            "Please restart the backend.",
        );
      }
    } catch (err) {
      errors.push(`Could not read backend version: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  const staticMountOk = await checkStaticMount();
  if (!staticMountOk) errors.push("Static asset mount (/static/projects) is not serving files.");

  return { backendReachable, apiVersionMatches, staticMountOk, storageOk, backendApiVersion, errors };
}
