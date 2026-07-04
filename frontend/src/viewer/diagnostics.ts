/** Structured viewer logging: "Opening Page 1" -> "HTML Loaded" ->
 * "CSS Loaded" -> "Shadow DOM Mounted" -> "Ready" (or an error at any
 * step). Every call is tagged [Viewer] so it's easy to filter in devtools
 * while debugging preview reliability. */
export function logViewerEvent(stage: string, details: Record<string, unknown> = {}): void {
  // eslint-disable-next-line no-console
  console.debug(`[Viewer] ${stage}`, details);
}
