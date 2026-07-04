import { ReactNode } from "react";

export interface EmptyStateProps {
  /** A small glyph/icon. */
  glyph?: ReactNode;
  /** One sentence — what's empty and why. */
  message: ReactNode;
  /** One action, if there is a next step (a Button, typically). */
  action?: ReactNode;
}

/** Icon + one sentence + one action (09_DESIGN_SYSTEM.md §6). Honest-UI
 * rule: empty states say what's missing or coming; they never fake data. */
export function EmptyState({ glyph, message, action }: EmptyStateProps) {
  return (
    <div className="lfui-empty">
      {glyph && <span className="lfui-empty-glyph" aria-hidden="true">{glyph}</span>}
      <div>{message}</div>
      {action}
    </div>
  );
}
