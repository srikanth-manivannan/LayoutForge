import { HTMLAttributes } from "react";

/** The status taxonomy (02_INFORMATION_ARCHITECTURE.md §states). Statuses
 * render through this component and nothing else, so the vocabulary and
 * colors stay identical on every surface. */
export type BadgeStatus =
  | "ready"
  | "processing"
  | "failed"
  | "pass"
  | "warning"
  | "error"
  | "neutral";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  status: BadgeStatus;
}

export function Badge({ status, className, children, ...rest }: BadgeProps) {
  const classes = ["lfui-badge", `lfui-badge--${status}`];
  if (className) classes.push(className);
  return (
    <span className={classes.join(" ")} {...rest}>
      {children}
    </span>
  );
}
