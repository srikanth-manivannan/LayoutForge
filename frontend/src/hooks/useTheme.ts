import { useSyncExternalStore } from "react";

import { getTheme, subscribeTheme, Theme } from "../theme/theme";

/** Reactive read of the current theme. Components that need to CHANGE the
 * theme dispatch the `view.setTheme`/`view.toggleTheme` commands instead of
 * importing the theme service directly. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribeTheme, getTheme);
}
