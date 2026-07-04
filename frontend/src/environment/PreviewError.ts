import { ApiError, getHealth, getVersion } from "../api/client";
import { EXPECTED_API_VERSION } from "./checkEnvironment";

export interface PreviewError {
  reason: string;
  expected?: string;
  suggestions: string[];
}

const DEFAULT_SUGGESTIONS = ["Restart the backend", "Verify backend version via /api/version", "Refresh the browser"];

/** Runs the guarded "before opening a project" sequence (version -> health
 * -> the actual request) so a failure produces a specific, actionable
 * PreviewError instead of a generic empty preview. */
export async function withPreviewErrorHandling<T>(
  expectedEndpoint: string,
  request: () => Promise<T>,
): Promise<{ data: T | null; error: PreviewError | null }> {
  try {
    await getVersion().then((version) => {
      if (version.api_version !== EXPECTED_API_VERSION) {
        throw new Error(
          `Backend API version mismatch (expected ${EXPECTED_API_VERSION}, got ${version.api_version}).`,
        );
      }
    });
    await getHealth();
  } catch (err) {
    return {
      data: null,
      error: {
        reason: err instanceof Error ? err.message : "Backend environment check failed.",
        expected: expectedEndpoint,
        suggestions: DEFAULT_SUGGESTIONS,
      },
    };
  }

  try {
    return { data: await request(), error: null };
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        data: null,
        error: {
          reason:
            err.status === 404
              ? "Backend endpoint not available."
              : `Request failed (status ${err.status}): ${err.message}`,
          expected: expectedEndpoint,
          suggestions: DEFAULT_SUGGESTIONS,
        },
      };
    }
    return {
      data: null,
      error: {
        reason: err instanceof Error ? err.message : "Unknown error.",
        expected: expectedEndpoint,
        suggestions: DEFAULT_SUGGESTIONS,
      },
    };
  }
}
