import { CSSProperties } from "react";

export interface SkeletonProps {
  width?: CSSProperties["width"];
  height?: CSSProperties["height"];
  className?: string;
}

/** Loading placeholder — skeletons over spinners for content areas
 * (PERFORMANCE.md UX consequences). */
export function Skeleton({ width = "100%", height = 14, className }: SkeletonProps) {
  return (
    <span
      className={className ? `lfui-skeleton ${className}` : "lfui-skeleton"}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}
