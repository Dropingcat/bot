# -*- coding: utf-8 -*-
"""
Тест: Проверка, что process_manager действительно вызывает emit_event
"""
import asyncio
import tempfile
import os
import textwrap

from config import process_config
original_retries = process_config.TASK_MAX_RETRIES
process_config.TASK_MAX_RETRIES = 0  # <-- Убираем повторы

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_process_manager_emit():
    print("🧪 Тест: process_manager вызывает emit_event")
    received_events = []

    async def handler(event):
        print(f"DEBUG: Получено событие: {event}")
        received_events.append(event)

    # Подписываемся на ВСЕ события (task_result, task_error, и т.д.)
    subscribe_async("task_result", handler)
    subscribe_async("task_error", handler)

    # Создаём временный скрипт, который завершается с ошибкой
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        import sys
        sys.exit(1)  # Искусственно вызываем ошибку
        """))
        script_path = f.name

    try:
        task_id = await enqueue_script(script_path, ["789"])
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

        # Проверим, что получили событие
        assert len(received_events) > 0, "❌ Событие не было получено"
        event = received_events[0]
        assert event["EVENT_TYPE"] in ["task_error", "task_result"], f"❌ Неправильный тип события: {event['EVENT_TYPE']}"

        print("✅ OK: process_manager вызывает emit_event")
    finally:
        os.unlink(script_path)
        process_config.TASK_MAX_RETRIES = original_retries  # <-- Восстанавливаем
        # clear_all_handlers() — убираем из finally


if __name__ == "__main__":
    asyncio.run(test_process_manager_emit())
    clear_all_handlers()  # <-- Очищаем в конце