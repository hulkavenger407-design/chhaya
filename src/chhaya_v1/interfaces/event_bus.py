"""
Event Bus Interface for Chhaya.
Provides abstractions for event-driven architecture.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable


class EventBus(ABC):
    """
    Abstract Base Class for an internal event bus.
    Allows decoupling of components by publishing and subscribing to events.
    """

    @abstractmethod
    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Publishes an event to the bus.

        Args:
            event_type (str): The name or type of the event.
            payload (dict[str, Any]): The data associated with the event.
        """
        pass

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """
        Subscribes a handler to a specific event type.

        Args:
            event_type (str): The name or type of the event to listen for.
            handler (Callable[[dict[str, Any]], None]): The callback function when the event occurs.
        """
        pass
