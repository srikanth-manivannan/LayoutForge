type Handler<T> = (payload: T) => void;

/** A minimal typed pub/sub bus, mirroring the backend's EventDispatcher
 * pattern so the viewer's lifecycle (ProjectOpened, PageLoaded, ZoomChanged,
 * SelectionChanged, ...) is observable without React owning that state. */
export class EventBus<Events extends object> {
  private handlers = new Map<keyof Events, Set<Handler<unknown>>>();

  on<K extends keyof Events>(event: K, handler: Handler<Events[K]>): () => void {
    const set = this.handlers.get(event) ?? new Set();
    set.add(handler as Handler<unknown>);
    this.handlers.set(event, set);
    return () => set.delete(handler as Handler<unknown>);
  }

  emit<K extends keyof Events>(event: K, payload: Events[K]): void {
    this.handlers.get(event)?.forEach((handler) => handler(payload));
  }
}
