import logging
from collections import defaultdict
from collections.abc import Callable

from app.events.base import Event

events_logger = logging.getLogger("layoutforge.events")

EventHandler = Callable[[Event], None]


class EventDispatcher:
    """A lightweight in-process pub/sub dispatcher. Handlers run
    synchronously, in registration order, on the publishing thread."""

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def subscribe(self, event_type: type[Event], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._global_handlers.append(handler)

    def publish(self, event: Event) -> None:
        for handler in self._global_handlers:
            handler(event)
        for handler in self._handlers.get(type(event), []):
            handler(event)


def log_event(event: Event) -> None:
    events_logger.info("%s %s", type(event).__name__, event)


dispatcher = EventDispatcher()
dispatcher.subscribe_all(log_event)
