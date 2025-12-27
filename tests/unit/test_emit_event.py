# -*- coding: utf-8 -*-
"""
Тест: Проверка, что emit_event действительно вызывает обработчики
"""
import asyncio
from core.event_bus import subscribe_async, emit_event, clear_all_handlers

async def test_emit_event():
    print("🧪 Тест: emit_event отправляет события")
    received_events = []

    async def handler(event):
        received_events.append(event)

    subscribe_async("test_event", handler)

    # Отправляем событие
    await emit_event("test_event", {"data": "ok", "user_id": 123})

    # Ждём, пока обработчик сработает
    for _ in range(10):  # 10 попыток по 0.1 сек = 1 сек
        if len(received_events) > 0:
            break
        await asyncio.sleep(0.1)

    assert len(received_events) == 1
    event = received_events[0]
    assert event["data"] == "ok"
    assert event["user_id"] == 123
    print("✅ OK: emit_event работает корректно")

    clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_emit_event())