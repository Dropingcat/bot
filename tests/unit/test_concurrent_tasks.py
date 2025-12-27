# -*- coding: utf-8 -*-
"""
Тест: Запуск нескольких задач одновременно → проверка ограничения
"""
import asyncio
import tempfile
import os
import textwrap

from config import process_config
original_max_tasks = process_config.MAX_CONCURRENT_TASKS
process_config.MAX_CONCURRENT_TASKS = 2  # Ограничим для теста

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script, get_active_task_count

async def test_concurrent_tasks():
    print("🧪 Тест: Параллельные задачи")
    received_events = []

    async def handler(event):
        received_events.append(event)

    subscribe_async("task_result", handler)

    # Создаём временный скрипт, который "спит" 0.5 секунды
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        import sys
        import time
        time.sleep(0.5)
        print("EVENT_TYPE:task_result")
        print("RESULT_TYPE:text")
        print(f"MESSAGE:Задача {sys.argv[1]} завершена")
        """))
        script_path = f.name

    try:
        tasks = []
        for i in range(5):  # 5 задач
            task_id = await enqueue_script(script_path, [str(i)])
            tasks.append(task_id)
        
        print(f"   Поставлено задач: {len(tasks)}")
        print(f"   Активных задач (ожидается <=2): {get_active_task_count()}")
        
        await asyncio.sleep(2)  # Ждём выполнения

        assert len(received_events) == 5
        messages = [e["MESSAGE"] for e in received_events]
        assert all("завершена" in m for m in messages)
        print("✅ OK: Все задачи выполнены, очередь отработала корректно")
    finally:
        os.unlink(script_path)
        process_config.MAX_CONCURRENT_TASKS = original_max_tasks
        clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_concurrent_tasks())