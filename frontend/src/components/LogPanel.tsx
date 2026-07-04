interface LogPanelProps {
  lines: string[];
}

export default function LogPanel({ lines }: LogPanelProps) {
  return (
    <footer className="lf-log-panel bg-dark text-light p-2">
      {lines.length === 0 ? (
        <div className="text-secondary">No active job.</div>
      ) : (
        lines.map((line, index) => <div key={index}>{line}</div>)
      )}
    </footer>
  );
}
