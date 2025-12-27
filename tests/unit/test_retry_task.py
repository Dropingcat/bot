# -*- coding: utf-8 -*-
"""
Тест: Скрипт падает → повтор → успех
"""
import asyncio
import tempfile
import os
import textwrap

from config import process_config
original_retries = process_config.TASK_MAX_RETRIES
original_delay = process_config.TASK_RETRY_DELAY_SEC
process_config.TASK_MAX_RETRIES = 2
process_config.TASK_RETRY_DELAY_SEC = 0.1  # 0.1 секунды для теста

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_retry_task():
    print("🧪 Тест: Задача с повтором")
    received_events = []

    async def handler(event):
        received_events.append(event)

    subscribe_async("task_result", handler)

    # Создаём временный скрипт, который в первый раз падает, во второй — работает
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
        # -*- coding: utf-8 -*-
        import sys
        import os
        flag_file = 'retry_flag.txt'
        if os.path.exists(flag_file):
            print("EVENT_TYPE:task_result")
            print("RESULT_TYPE:text")
            print("MESSAGE:Успех после повтора")
            os.unlink(flag_file)
        else:
            with open(flag_file, 'w') as fl:
                fl.write('1')
            sys.exit(1)
        """))
        script_path = f.name

    try:
        task_id = await enqueue_script(script_path, ["202"])
        print(f"   Задача поставлена: {task_id}")
        
        await asyncio.sleep(1)  # Ждём выполнения

        assert len(received_events) == 1
        event = received_events[0]
        assert event["EVENT_TYPE"] == "task_result"
        assert event["MESSAGE"] == "Успех после повтора"
        print("✅ OK: Повтор сработал корректно")
    finally:
        if os.path.exists('retry_flag.txt'):
            os.unlink('retry_flag.txt')
        os.unlink(script_path)
        process_config.TASK_MAX_RETRIES = original_retries
        process_config.TASK_RETRY_DELAY_SEC = original_delay
        clear_all_handlers()


if __name__ == "__main__":
    asyncio.run(test_retry_task())