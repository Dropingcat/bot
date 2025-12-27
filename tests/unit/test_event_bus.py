# -*- coding: utf-8 -*-
"""
Тесты для core/event_bus.py
"""
import asyncio
from core.event_bus import subscribe_async, emit_event, clear_all_handlers


async def test_event_bus():
    received_events = []

    async def handler(event):
        received_events.append(event)

    subscribe_async("test_event", handler)
    await emit_event("test_event", {"data": "ok", "user_id": 123})

    await asyncio.sleep(0.05)  # Дадим событию обработаться

    assert len(received_events) == 1
    assert received_events[0]["data"] == "ok"
    assert received_events[0]["user_id"] == 123

    clear_all_handlers()
    print("✅ test_event_bus passed")


async def test_event_bus_multiple_handlers():
    received_events = []

    async def handler1(event):
        received_events.append(("h1", event["data"]))

    async def handler2(event):
        received_events.append(("h2", event["data"]))

    subscribe_async("multi_event", handler1)
    subscribe_async("multi_event", handler2)

    await emit_event("multi_event", {"data": "multi"})

    await asyncio.sleep(0.05)

    assert len(received_events) == 2
    assert ("h1", "multi") in received_events
    assert ("h2", "multi") in received_events

    clear_all_handlers()
    print("✅ test_event_bus_multiple_handlers passed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_event_bus())
    asyncio.run(test_event_bus_multiple_handlers())