# -*- coding: utf-8 -*-
"""
Тест: Скрипт "зависает" → таймаут → событие task_error
"""
import asyncio
import tempfile
import os
import textwrap

from config import process_config
original_timeout = process_config.TASK_TIMEOUT_SEC
process_config.TASK_TIMEOUT_SEC = 1  # 1 секунда для теста

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_timeout_task():
    print("🧪 Тест: Задача с таймаутом")
    received_events = []

    async def handler(event):
        received_events.append(event)

    subscribe_async("task_error", handler)

    # Создаём временный скрипт, который "спит" 5 секунд
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        import time
        time.sleep(5)
        """))
        script_path = f.name

    try:
        task_id = await enqueue_script(script_path, ["101"])
        print(f"   Задача поставлена: {task_id}")
        
        await asyncio.sleep(2)  # Ждём больше таймаута

        assert len(received_events) == 1
        event = received_events[0]
        assert event["EVENT_TYPE"] == "task_error"
        assert "таймаут" in event["ERROR_MESSAGE"].lower()
        print("✅ OK: Таймаут получен корректно")
    finally:
        os.unlink(script_path)
        process_config.TASK_TIMEOUT_SEC = original_timeout
        clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_timeout_task())