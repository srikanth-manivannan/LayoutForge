import { HTMLAttributes } from "react";

export interface ToolbarProps extends HTMLAttributes<HTMLDivElement> {
  "aria-label": string;
}

/** Horizontal command strip. Children are Buttons/IconButtons/selects that
 * dispatch commands; use ToolbarSeparator and ToolbarSpacer for grouping. */
export function Toolbar({ className, ...rest }: ToolbarProps) {
  return <div role="toolbar" className={className ? `lfui-toolbar ${className}` : "lfui-toolbar"} {...rest} />;
}

export function ToolbarSeparator() {
  return <span className="lfui-toolbar-sep" aria-hidden="true" />;
}

export function ToolbarSpacer() {
  return <span className="lfui-toolbar-spacer" aria-hidden="true" />;
}
