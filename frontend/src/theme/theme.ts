/** Theme service — the one owner of the current UI theme.
 *
 * Dark mode is a token swap (`data-lf-theme` on <html>, see
 * styles/tokens.css), never a component fork; `data-bs-theme` is kept in
 * sync so Bootstrap's own dark-mode rules engage too. The rendered document
 * page is intentionally outside the theme's reach.
 *
 * UI controls change the theme through the `view.setTheme`/`view.toggleTheme`
 * commands, which call into this module — components subscribe via
 * `useTheme()` (hooks/useTheme.ts). */

export type Theme = "light" | "dark";

const STORAGE_KEY = "lf.theme";
const listeners = new Set<() => void>();

function readStored(): Theme {
  try {
    return localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

let current: Theme = readStored();

function apply(theme: Theme) {
  const root = document.documentElement;
  if (theme === "dark") root.setAttribute("data-lf-theme", "dark");
  else root.removeAttribute("data-lf-theme");
  root.setAttribute("data-bs-theme", theme);
}

export function getTheme(): Theme {
  return current;
}

export function setTheme(theme: Theme) {
  if (theme === current) return;
  current = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* private-mode storage failures must never break theming */
  }
  apply(theme);
  listeners.forEach((listener) => listener());
}

export function toggleTheme() {
  setTheme(current === "dark" ? "light" : "dark");
}

/** Apply the persisted theme before first paint (called from main.tsx). */
export function initTheme() {
  apply(current);
}

export function subscribeTheme(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
