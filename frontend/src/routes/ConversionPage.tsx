import { useWorkspace } from "../context/WorkspaceContext";

/** Shows the one job currently tracked by `useProjectWorkspace`. A true
 * multi-job queue (concurrent conversions, history) is the Conversion
 * Monitor's job in sub-phase 2C — this page is honest about today's
 * single-job-tracking capability rather than presenting a queue UI with
 * nothing behind it. */
export default function ConversionPage() {
  const { activeJob, logLines } = useWorkspace();

  return (
    <div className="p-4">
      <h5 className="mb-3">Conversion</h5>
      {!activeJob ? (
        <p className="text-muted">No conversion is currently running.</p>
      ) : (
        <div className="lf-job-card mb-4" style={{ maxWidth: 480 }}>
          <div className="d-flex justify-content-between small mb-1">
            <span>Job {activeJob.id}</span>
            <span>{activeJob.status}</span>
          </div>
          <div className="d-flex justify-content-between small mb-1">
            <span>{activeJob.stage ?? "—"}</span>
            <span>{activeJob.progress}%</span>
          </div>
          <div className="progress" style={{ height: 6 }}>
            <div className="progress-bar" style={{ width: `${activeJob.progress}%` }} />
          </div>
          {activeJob.error_message && <div className="text-danger small mt-2">{activeJob.error_message}</div>}
        </div>
      )}

      <h6 className="text-uppercase text-muted small mb-2">Job Log</h6>
      <div className="lf-log-snippet" style={{ maxWidth: 640 }}>
        {logLines.length === 0 ? (
          <div className="text-muted small">No log entries yet.</div>
        ) : (
          logLines.map((line, index) => <div key={index}>{line}</div>)
        )}
      </div>
    </div>
  );
}
