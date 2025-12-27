# tests/integration/test_chain_manual.py

import asyncio
from core.process_manager import enqueue_script
from core.event_bus import subscribe_async

async def on_result(data):
    print("✅ Получен результат:", data)

async def main():
    # Подписываемся на событие
    subscribe_async("task_result", on_result)
    
    # ЗАПУСКАЕМ СКРИПТ — ОБЯЗАТЕЛЬНО С await
    task_id = await enqueue_script(
        "scripts/weather/weather_today_script.py",
        ["55.75", "37.62", "123"]
    )
    print("Запущена задача:", task_id)

    # Ждём завершения (например, 10 секунд)
    await asyncio.sleep(10)

# Запускаем асинхронную функцию
if __name__ == "__main__":
    asyncio.run(main())