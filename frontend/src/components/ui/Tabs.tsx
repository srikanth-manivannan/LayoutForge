import { ReactNode } from "react";

export interface TabItem {
  id: string;
  label: ReactNode;
  disabled?: boolean;
  /** Honest tooltip for disabled tabs, e.g. "Planned for Phase 5". */
  title?: string;
}

export interface TabsProps {
  items: TabItem[];
  activeId: string;
  onSelect: (id: string) => void;
  "aria-label": string;
  className?: string;
}

/** Accent-underline tab strip (CenterDock style). Purely presentational —
 * the caller owns which tab is active (e.g. via `?panel=` in the URL). */
export function Tabs({ items, activeId, onSelect, className, ...rest }: TabsProps) {
  return (
    <div role="tablist" aria-label={rest["aria-label"]} className={className ? `lfui-tabs ${className}` : "lfui-tabs"}>
      {items.map((item) => (
        <button
          key={item.id}
          role="tab"
          type="button"
          aria-selected={item.id === activeId}
          disabled={item.disabled}
          title={item.title}
          className={item.id === activeId ? "lfui-tab lfui-tab--active" : "lfui-tab"}
          onClick={() => onSelect(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
