from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Event:
    """Base class for all internal domain events. Initially every event is
    just logged; the same dispatcher can later drive notifications,
    WebSockets, audit trails, or analytics without touching call sites."""

    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), kw_only=True)
