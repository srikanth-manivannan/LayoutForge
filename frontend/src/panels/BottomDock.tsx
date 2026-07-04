import { useCallback, useEffect, useState } from "react";

import { getLogs, JobRead, LogStream } from "../api/client";
import LogPanel from "../components/LogPanel";
import { Badge, Button, Progress, Tabs } from "../components/ui";

type BottomTab = "job" | "monitor" | LogStream;

interface BottomDockProps {
  logLines: string[];
  activeJob: JobRead | null;
  /** Collapsed = only the tab strip is visible (the workspace default —
   * logs never eat canvas height unless asked for). */
  collapsed: boolean;
  onToggle: () => void;
  onExpand: () => void;
}

/** 2C bottom dock: the existing job log plus the three backend log streams
 * (fixed allow-list — the endpoint accepts nothing else) and the Conversion
 * Monitor. Streams are fetched on demand and on manual refresh — no
 * background polling for logs nobody is looking at. */
export default function BottomDock({ logLines, activeJob, collapsed, onToggle, onExpand }: BottomDockProps) {
  const [tab, setTab] = useState<BottomTab>("job");
  const [streamLines, setStreamLines] = useState<string[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isStream = tab === "application" || tab === "conversion" || tab === "performance";

  const refresh = useCallback(async () => {
    if (!isStream) return;
    setLoading(true);
    setStreamError(null);
    try {
      const result = await getLogs(tab as LogStream, 200);
      setStreamLines(result.lines);
    } catch (error) {
      setStreamError(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }, [tab, isStream]);

  useEffect(() => {
    setStreamLines([]);
    if (isStream) void refresh();
  }, [tab, isStream, refresh]);

  return (
    <footer className="lf-surface border-top d-flex flex-column h-100">
      <div className="d-flex align-items-center">
        <Tabs
          aria-label="Bottom dock"
          className="flex-grow-1 border-0"
          activeId={collapsed ? "" : tab}
          onSelect={(id) => {
            setTab(id as BottomTab);
            onExpand();
          }}
          items={[
            { id: "job", label: "Job log" },
            { id: "monitor", label: "Conversion Monitor" },
            { id: "application", label: "Application" },
            { id: "conversion", label: "Conversion" },
            { id: "performance", label: "Performance" },
          ]}
        />
        {!collapsed && isStream && (
          <Button size="sm" variant="ghost" onClick={refresh} disabled={loading}>
            ↻ Refresh
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="me-2"
          title={collapsed ? "Expand logs (Ctrl+J)" : "Collapse logs (Ctrl+J)"}
          onClick={onToggle}
        >
          {collapsed ? "▴" : "▾"}
        </Button>
      </div>

      {collapsed ? null : (
      <div className="flex-grow-1 overflow-auto">
        {tab === "job" && <LogPanel lines={logLines} />}

        {tab === "monitor" && <ConversionMonitor job={activeJob} />}

        {isStream &&
          (streamError ? (
            <p className="small text-danger p-2 mb-0">Failed to load {tab} log: {streamError}</p>
          ) : (
            <pre
              className="small p-2 mb-0"
              style={{ fontFamily: "var(--lf-font-mono)", fontSize: "var(--lf-fs-xs)", color: "var(--lf-text-muted)" }}
            >
              {streamLines.length === 0 ? (loading ? "Loading…" : "No lines.") : streamLines.join("\n")}
            </pre>
          ))}
      </div>
      )}
    </footer>
  );
}

/** Honest single-job monitor: exactly what the polling loop tracks today
 * (one job at a time) — a true multi-job queue arrives with Phase 7 batch. */
function ConversionMonitor({ job }: { job: JobRead | null }) {
  if (!job) {
    return <p className="small text-muted p-2 mb-0">No conversion tracked in this session.</p>;
  }
  const status =
    job.status === "completed" ? "ready" : job.status === "failed" ? "failed" : ("processing" as const);
  return (
    <div className="p-2 small d-flex flex-column gap-2" style={{ maxWidth: 560 }}>
      <div className="d-flex align-items-center gap-2">
        <strong>Job</strong>
        <span style={{ fontFamily: "var(--lf-font-mono)", fontSize: "var(--lf-fs-xs)" }}>{job.id.slice(0, 8)}…</span>
        <Badge status={status}>{job.status}</Badge>
        {job.stage && <span className="text-muted">stage: {job.stage}</span>}
      </div>
      <div className="d-flex align-items-center gap-2">
        <Progress aria-label="Job progress" percent={job.progress ?? 0} className="flex-grow-1" />
        <span className="text-muted">{job.progress ?? 0}%</span>
      </div>
      {job.error_message && <div className="text-danger">{job.error_message}</div>}
    </div>
  );
}
