# -*- coding: utf-8 -*-
"""
Тест: Скрипт ничего не выводит → событие "нет данных"
"""
import asyncio
import tempfile
import os
import textwrap

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_empty_output_task():
    print("🧪 Тест: Задача с пустым выводом")
    received_events = []

    async def handler(event):
        received_events.append(event)

    subscribe_async("task_result", handler)

    # Создаём временный скрипт, который ничего не выводит
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        # Пустой скрипт
        """))
        script_path = f.name

    try:
        task_id = await enqueue_script(script_path, ["303"])
        print(f"   Задача поставлена: {task_id}")
        
        await asyncio.sleep(1)  # Дадим время на выполнение

        assert len(received_events) == 1
        event = received_events[0]
        assert event["EVENT_TYPE"] == "task_result"
        assert event["RESULT_TYPE"] == "text"
        assert "Нет данных" in event["MESSAGE"]
        print("✅ OK: Событие 'пустой результат' получено корректно")
    finally:
        os.unlink(script_path)
        clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_empty_output_task())