# test_chain_manual.py
from core.process_manager import enqueue_script
from core.event_bus import subscribe_async
import asyncio

async def on_result(data):
    print("✅ Получен результат:", data)

async def main():
    subscribe_async("task_result", on_result)
    task_id = enqueue_script("scripts/weather/weather_today_script.py", ["55.75", "37.62", "123"])
    print("Запущена задача:", task_id)
    await asyncio.sleep(10)  # ждём

asyncio.run(main())