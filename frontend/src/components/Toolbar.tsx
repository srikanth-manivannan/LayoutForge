import { EnvironmentCheckResult } from "../environment/checkEnvironment";

interface ToolbarProps {
  environment: EnvironmentCheckResult | null;
  isChecking: boolean;
  onRecheck: () => void;
}

function StatusBadge({ label, ok }: { label: string; ok: boolean | null }) {
  const badgeClass = ok === null ? "text-bg-secondary" : ok ? "text-bg-success" : "text-bg-danger";
  const symbol = ok === null ? "…" : ok ? "✔" : "✗";
  return (
    <span className={`badge ${badgeClass}`}>
      {label} {symbol}
    </span>
  );
}

export default function Toolbar({ environment, isChecking, onRecheck }: ToolbarProps) {
  return (
    <header className="d-flex align-items-center justify-content-between px-3 py-2 border-bottom lf-surface">
      <span className="fw-semibold">LayoutForge</span>
      <div className="d-flex align-items-center gap-2">
        <StatusBadge label="Backend" ok={environment ? environment.backendReachable : null} />
        <StatusBadge label="Storage" ok={environment ? environment.storageOk : null} />
        <StatusBadge label="Static" ok={environment ? environment.staticMountOk : null} />
        <StatusBadge label="API" ok={environment ? environment.apiVersionMatches : null} />
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          disabled={isChecking}
          onClick={onRecheck}
          title="Re-run environment check"
        >
          {isChecking ? "Checking…" : "↻"}
        </button>
      </div>
    </header>
  );
}
