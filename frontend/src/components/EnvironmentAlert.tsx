import { EnvironmentCheckResult, EXPECTED_API_VERSION } from "../environment/checkEnvironment";

interface EnvironmentAlertProps {
  environment: EnvironmentCheckResult | null;
}

/** A blocking, can't-miss-it banner for the two failures that mean nothing
 * else in the app can be trusted: the backend isn't reachable, or it's
 * running an API version this frontend wasn't built against. Per
 * instruction: never fail silently.
 *
 * Always renders the wrapper div (collapsing to ~0 height when there's
 * nothing to show) rather than returning null, so it keeps occupying its
 * row in ShellLayout's grid — returning null here would shift every row
 * below it up by one. */
export default function EnvironmentAlert({ environment }: EnvironmentAlertProps) {
  if (!environment) return <div />;

  if (!environment.backendReachable) {
    return (
      <div className="alert alert-danger rounded-0 mb-0 py-2 px-3">
        <strong>Backend unreachable.</strong> The app cannot reach the backend API. Start it with{" "}
        <code>uvicorn app.main:app --port 8000</code> from <code>backend/</code>, then click the ↻ button above.
      </div>
    );
  }

  if (!environment.apiVersionMatches) {
    return (
      <div className="alert alert-danger rounded-0 mb-0 py-2 px-3">
        <strong>Backend version mismatch detected.</strong> Please restart the backend
        {environment.backendApiVersion !== null && (
          <>
            {" "}
            (expected API version {EXPECTED_API_VERSION}, got {environment.backendApiVersion})
          </>
        )}
        .
      </div>
    );
  }

  return <div />;
}
