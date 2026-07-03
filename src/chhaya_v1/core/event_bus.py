"""
In-Memory Event Bus Implementation.
"""

from typing import Any, Callable, Dict, List
import structlog

from chhaya_v1.interfaces.event_bus import EventBus

logger = structlog.get_logger(__name__)


class InMemoryEventBus(EventBus):
    """
    A simple synchronous, in-memory implementation of the EventBus.
    """

    def __init__(self) -> None:
        # Dictionary mapping event_type to a list of handler functions
        self._subscribers: Dict[str, List[Callable[[dict[str, Any]], None]]] = {}
        logger.debug("Initialized InMemoryEventBus")

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Publishes an event to all registered subscribers.
        """
        logger.debug("Publishing event", event_type=event_type)

        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug("No subscribers for event", event_type=event_type)
            return

        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                # Catch exceptions so one failing handler doesn't crash the others
                logger.error("Error in event handler", event_type=event_type, error=str(e))

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """
        Registers a handler for a specific event type.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)
        logger.info("Subscribed to event", event_type=event_type, handler=handler.__name__)
