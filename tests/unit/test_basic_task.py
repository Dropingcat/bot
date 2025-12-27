# -*- coding: utf-8 -*-
"""
Тест: Запуск простого скрипта → получение события через event_bus
"""
import asyncio
import tempfile
import os
import textwrap

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_basic_task():
    print("🧪 Тест: Базовый запуск задачи")
    received_events = []

    async def handler(event):
        received_events.append(event)

    subscribe_async("task_result", handler)

    # Создаём временный скрипт
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        import sys
        print("EVENT_TYPE:task_result")
        print("RESULT_TYPE:graph")
        print(f"USER_ID:{sys.argv[1] if len(sys.argv) > 1 else 123}")
        print("FILE_PATH:/app/data/test_graph.png")
        """))
        script_path = f.name

    try:
        task_id = await enqueue_script(script_path, ["456"])
        print(f"   Задача поставлена: {task_id}")
        
        await asyncio.sleep(1)  # Дадим время на выполнение

        assert len(received_events) == 1
        event = received_events[0]
        assert event["EVENT_TYPE"] == "task_result"
        assert event["USER_ID"] == "456"
        assert event["RESULT_TYPE"] == "graph"
        print("✅ OK: Событие получено корректно")
    finally:
        os.unlink(script_path)
        clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_basic_task())