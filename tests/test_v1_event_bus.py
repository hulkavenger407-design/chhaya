"""
Tests for Chhaya Event Bus.
"""

from typing import Any, Dict
from chhaya_v1.core.event_bus import InMemoryEventBus


def test_event_bus_subscribe_and_publish():
    bus = InMemoryEventBus()
    received_events = []

    def test_handler(payload: Dict[str, Any]):
        received_events.append(payload)

    bus.subscribe("agent_run_completed", test_handler)

    # Publish relevant event
    bus.publish("agent_run_completed", {"agent_id": "123", "status": "success"})
    assert len(received_events) == 1
    assert received_events[0]["agent_id"] == "123"

    # Publish irrelevant event
    bus.publish("agent_run_started", {"agent_id": "123"})
    assert len(received_events) == 1  # Should not have increased


def test_event_bus_multiple_subscribers():
    bus = InMemoryEventBus()

    counter = {"a": 0, "b": 0}

    def handler_a(payload: Dict[str, Any]):
        counter["a"] += 1

    def handler_b(payload: Dict[str, Any]):
        counter["b"] += 1

    bus.subscribe("system_startup", handler_a)
    bus.subscribe("system_startup", handler_b)

    bus.publish("system_startup", {})

    assert counter["a"] == 1
    assert counter["b"] == 1


def test_event_bus_handler_exception_isolation():
    """Ensure one failing handler doesn't crash the bus or stop other handlers."""
    bus = InMemoryEventBus()

    counter = {"success": 0}

    def failing_handler(payload: Dict[str, Any]):
        raise RuntimeError("I crashed!")

    def successful_handler(payload: Dict[str, Any]):
        counter["success"] += 1

    bus.subscribe("test_event", failing_handler)
    bus.subscribe("test_event", successful_handler)

    # Should not raise an exception
    bus.publish("test_event", {})

    # The successful handler should still have executed
    assert counter["success"] == 1
