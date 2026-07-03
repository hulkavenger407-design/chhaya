import asyncio
from typing import Any, Callable, Dict, List
import structlog

logger = structlog.get_logger(__name__)

class EventBus:
    """
    Async Pub/Sub Event Bus for JARVIS V3.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe a callback to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug("subscribed_to_event", event_type=event_type, callback=callback.__name__)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe a callback from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug("unsubscribed_from_event", event_type=event_type, callback=callback.__name__)
            except ValueError:
                pass

    async def publish(self, event_type: str, payload: Any = None) -> None:
        """Publish an event to all subscribers asynchronously."""
        if event_type not in self._subscribers:
            return

        callbacks = self._subscribers[event_type]

        # Create tasks for all subscribers
        tasks = []
        for callback in callbacks:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(asyncio.create_task(callback(payload)))
            else:
                # Run sync callbacks in thread pool to avoid blocking
                tasks.append(asyncio.to_thread(callback, payload))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error("event_subscriber_error", error=str(res), event_type=event_type)

# Global singleton
event_bus = EventBus()
