# -*- coding: utf-8 -*-
"""
Тест: запуск простого скрипта через process_manager
"""

import asyncio
import tempfile
import os
import textwrap

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_simple_script():
    print("🧪 Тест: запуск простого скрипта через process_manager")
    received_events = []

    async def handler(event):
        print(f"📡 Получено событие: {event}")
        received_events.append(event)

    subscribe_async("task_result", handler)

    # Создаём простейший скрипт
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        print("EVENT_TYPE:task_result")
        print("RESULT_TYPE:graph")
        print("USER_ID:123")
        print("FILE_PATH:/app/data/test_graph.png")
        print("SUMMARY:Тестовое сообщение")
        """))
        script_path = f.name

    try:
        task_id = await enqueue_script(script_path, ["123"])
        print(f"✅ Задача поставлена: {task_id}")

        # Ждём 5 секунд
        for i in range(10):
            if len(received_events) > 0:
                break
            print(f"⏳ Ждём событие... {i + 1}/10")
            await asyncio.sleep(0.5)

        print(f"📊 Получено событий: {len(received_events)}")
        if received_events:
            print(f"✅ Событие: {received_events[0]}")
            assert received_events[0]["EVENT_TYPE"] == "task_result"
            assert received_events[0]["USER_ID"] == "123"
            print("🎉 OK: Событие получено")
        else:
            print("❌ Нет событий")
    finally:
        os.unlink(script_path)
        clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_simple_script())