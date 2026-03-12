"""Event bus for server-sent events fan-out."""

import asyncio
import contextlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """Async event bus with fan-out to multiple subscribers via asyncio.Queue."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Create a new subscription queue."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscription queue."""
        async with self._lock:
            with contextlib.suppress(ValueError):
                self._subscribers.remove(queue)

    async def publish(self, event: dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full, dropping event")
