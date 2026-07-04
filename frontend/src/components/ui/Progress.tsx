export interface ProgressProps {
  /** 0–100. Progress is always determinate and honest — if you don't know
   * the percentage, show a Skeleton or stage list instead. */
  percent: number;
  "aria-label": string;
  className?: string;
}

export function Progress({ percent, className, ...rest }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped)}
      aria-label={rest["aria-label"]}
      className={className ? `lfui-progress ${className}` : "lfui-progress"}
    >
      <i style={{ width: `${clamped}%` }} />
    </div>
  );
}
