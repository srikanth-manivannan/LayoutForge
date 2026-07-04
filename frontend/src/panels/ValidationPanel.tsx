import { useCallback, useEffect, useRef, useState } from "react";

import { Badge, Button, EmptyState, Progress, Toolbar, ToolbarSpacer } from "../components/ui";
import { useDocumentManager } from "../context/DocumentManagerContext";
import { useAppEventBus } from "../context/EventBusContext";
import { ValidationFinding, ValidationRun, WorkerResponse } from "../validation/types";
import { WorkspaceService } from "../workspace/WorkspaceService";

interface ValidationPanelProps {
  projectId: string;
  workspace: WorkspaceService;
  /** Jump the operator to a finding: switch the center dock to the Viewer
   * and select/highlight the object (same navigation + selection pipeline
   * search uses). */
  onReveal: (finding: ValidationFinding) => void;
}

const EMPTY_RUN: ValidationRun = { findings: [], pagesChecked: 0, pageCount: 0, finishedAt: null };

/** Automated proofing checks (2C): runs the validation engine in a Web
 * Worker — cancelable, per-page, streaming results into the table as they
 * arrive — so a 2,000-page run never blocks the canvas. Results persist in
 * the Document Manager, surviving tab switches. */
export default function ValidationPanel({ projectId, workspace, onReveal }: ValidationPanelProps) {
  const documents = useDocumentManager();
  const bus = useAppEventBus();
  const [run, setRun] = useState<ValidationRun>(() => documents.getValidationRun(projectId) ?? EMPTY_RUN);
  const [running, setRunning] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const workerRef = useRef<Worker | null>(null);

  const stop = useCallback(() => {
    workerRef.current?.terminate();
    workerRef.current = null;
    setRunning(false);
  }, []);

  const start = useCallback(() => {
    stop();
    setFailure(null);
    setSelectedIndex(-1);
    const idmUrl = workspace.resolveStaticUrl("idm.json");
    if (!idmUrl) {
      // Never fail silently (honest-UI rule) — this state means the route
      // hasn't opened the project in the WorkspaceService yet.
      setFailure("No project open in the workspace yet — try again in a moment.");
      return;
    }

    const next: ValidationRun = { ...EMPTY_RUN, findings: [] };
    setRun(next);
    setRunning(true);

    const worker = new Worker(new URL("../validation/validationWorker.ts", import.meta.url), { type: "module" });
    workerRef.current = worker;
    worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const message = event.data;
      if (message.type === "progress") {
        next.findings = [...next.findings, ...message.findings];
        next.pagesChecked += 1;
        next.pageCount = message.pageCount;
        const snapshot = { ...next, findings: next.findings };
        setRun(snapshot);
      } else if (message.type === "done") {
        const finished = { ...next, pageCount: message.pageCount, finishedAt: Date.now() };
        documents.setValidationRun(projectId, finished);
        setRun(finished);
        stop();
      } else if (message.type === "error") {
        setFailure(message.message);
        stop();
      }
    };
    worker.onerror = (event) => {
      setFailure(event.message || "Validation worker failed");
      stop();
    };
    worker.postMessage({ type: "run", idmUrl });
  }, [documents, projectId, stop, workspace]);

  // The `validate.run` command (palette/toolbar) triggers runs through the
  // app event bus — no direct reference to this panel exists anywhere.
  useEffect(() => bus.on("validation:run", () => start()), [bus, start]);
  useEffect(() => () => workerRef.current?.terminate(), []);

  const pagesWithFindings = new Set(run.findings.map((finding) => finding.page));
  const passCount = Math.max(0, run.pagesChecked - pagesWithFindings.size);
  const warnings = run.findings.filter((finding) => finding.severity === "warning").length;
  const errors = run.findings.filter((finding) => finding.severity === "error").length;

  return (
    <div className="d-flex flex-column h-100 lf-surface">
      <Toolbar aria-label="Validation tools">
        <Button size="sm" variant="primary" disabled={running} onClick={start}>
          ▶ Run all
        </Button>
        {running && (
          <Button size="sm" onClick={stop}>
            Cancel
          </Button>
        )}
        <ToolbarSpacer />
        {run.pageCount > 0 && (
          <>
            <Progress
              aria-label="Validation progress"
              percent={(run.pagesChecked / Math.max(1, run.pageCount)) * 100}
              className="me-2"
            />
            <span className="small text-muted" style={{ minWidth: 90 }}>
              {run.pagesChecked} / {run.pageCount} pages
            </span>
          </>
        )}
        {run.finishedAt && (
          <span className="small text-muted">checked {new Date(run.finishedAt).toLocaleTimeString()}</span>
        )}
      </Toolbar>

      {run.pagesChecked > 0 && (
        <div className="d-flex align-items-center gap-2 px-3 py-2 border-bottom">
          <Badge status="pass">✓ {passCount} pass</Badge>
          <Badge status="warning">⚠ {warnings} warnings</Badge>
          <Badge status={errors > 0 ? "error" : "neutral"}>✕ {errors} errors</Badge>
        </div>
      )}

      <div className="flex-grow-1 overflow-auto">
        {failure ? (
          <EmptyState glyph="✕" message={<span>Validation failed: {failure}</span>} action={<Button size="sm" onClick={start}>Retry</Button>} />
        ) : run.pagesChecked === 0 && !running ? (
          <EmptyState
            glyph="✓"
            message="No validation yet — checks layout, text, fonts, and assets from the IDM."
            action={
              <Button size="sm" variant="primary" onClick={start}>
                ▶ Run all
              </Button>
            }
          />
        ) : run.findings.length === 0 ? (
          <EmptyState glyph="✓" message={running ? "Checking…" : `All ${run.pagesChecked} checked pages pass.`} />
        ) : (
          <table className="lf-table" aria-label="Validation findings">
            <thead>
              <tr>
                <th style={{ width: 70 }}>Sev</th>
                <th style={{ width: 60 }}>Page</th>
                <th style={{ width: 110 }}>Object</th>
                <th>Message</th>
              </tr>
            </thead>
            <tbody>
              {run.findings.map((finding, index) => (
                <tr
                  key={`${finding.page}-${finding.objectId}-${index}`}
                  className={index === selectedIndex ? "selected" : undefined}
                  onClick={() => {
                    setSelectedIndex(index);
                    onReveal(finding);
                  }}
                >
                  <td>
                    <Badge status={finding.severity}>{finding.severity === "error" ? "✕" : "⚠"}</Badge>
                  </td>
                  <td>{finding.page}</td>
                  <td className="mono">{finding.objectId ? `${finding.objectId.slice(0, 8)}…` : "—"}</td>
                  <td>{finding.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
