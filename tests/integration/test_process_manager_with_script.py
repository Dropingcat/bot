# -*- coding: utf-8 -*-
"""
Интеграционный тест: process_manager + скрипт + event_bus
"""
import asyncio
from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script, init_process_manager

async def test_process_manager_with_script():
    print("🧪 Тест: process_manager + test_output_script")
    
    # === ИНИЦИАЛИЗИРУЕМ PROCESS MANAGER ===
    init_process_manager()
    
    received_events = []

    async def handler(event):
        print(f"DEBUG: Получено событие: {event}")
        received_events.append(event)

    # Подписываемся на события
    subscribe_async("task_result", handler)
    subscribe_async("task_error", handler)

    try:
        # Запускаем тестовый скрипт
        task_id = await enqueue_script("tests/unit/test_output.py", ["55.75", "37.62", "123"])
        print(f"   Задача поставлена: {task_id}")
        
        # Ждём событие с таймаутом
        for _ in range(10):  # 10 попыток по 0.2 сек = 2 сек
            if len(received_events) > 0:
                break
            await asyncio.sleep(0.2)

        print(f"   Получено событий: {len(received_events)}")
        if received_events:
            print(f"   Первое событие: {received_events[0]}")
        else:
            print("   ❌ Никаких событий не получено")

        # Проверим, что получили правильное событие
        assert len(received_events) > 0, "❌ Событие не было получено"
        event = received_events[0]
        assert event["EVENT_TYPE"] == "task_result", f"❌ Неправильный тип события: {event['EVENT_TYPE']}"
        assert event["USER_ID"] == "123", f"❌ Неправильный user_id: {event['USER_ID']}"
        assert event["MESSAGE"] == "Hello from subprocess!", f"❌ Неправильное сообщение: {event['MESSAGE']}"

        print("✅ OK: process_manager корректно обработал скрипт и отправил событие")
    finally:
        # Очищаем в конце
        clear_all_handlers()

if __name__ == "__main__":
    asyncio.run(test_process_manager_with_script())