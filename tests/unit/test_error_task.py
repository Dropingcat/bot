# -*- coding: utf-8 -*-
"""
Тест: Скрипт завершается с ошибкой → событие task_error
"""
import asyncio
import tempfile
import os
import textwrap

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_error_task():
    print("🧪 Тест: Задача с ошибкой")
    received_events = []

    async def handler(event):
        received_events.append(event)

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
        
        assert len(received_events) == 1
        event = received_events[0]
        assert event["EVENT_TYPE"] == "task_error"
        assert event["USER_ID"] == "789"
        assert "ERROR_MESSAGE" in event
        print("✅ OK: Ошибка получена корректно")
    finally:
        os.unlink(script_path)
        clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_error_task())