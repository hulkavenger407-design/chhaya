import pytest
import asyncio
from chhaya_v2.core.engine.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    bus = EventBus()
    received_payloads = []

    def sync_callback(payload):
        received_payloads.append(payload)

    async def async_callback(payload):
        received_payloads.append(payload)

    bus.subscribe("test_event", sync_callback)
    bus.subscribe("test_event", async_callback)

    await bus.publish("test_event", {"key": "value"})

    assert len(received_payloads) == 2
    assert received_payloads[0] == {"key": "value"}
    assert received_payloads[1] == {"key": "value"}

@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    bus = EventBus()
    call_count = 0

    def callback(payload):
        nonlocal call_count
        call_count += 1

    bus.subscribe("test_event", callback)
    await bus.publish("test_event")
    assert call_count == 1

    bus.unsubscribe("test_event", callback)
    await bus.publish("test_event")
    assert call_count == 1
