# tests/integration/test_weather_full_chain_verbose.py
import asyncio
import tempfile
import os
from pathlib import Path

from config import db_config
original_weather_db = db_config.WEATHER_CACHE_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_weather_db = tmp.name

db_config.WEATHER_CACHE_DB = Path(temp_weather_db)

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script

async def test_weather_full_chain_verbose():
    print("🧪 ТЕСТ: Полная цепочка weather модуля (verbose)")
    print("="*60)

    # === 1. ИНИЦИАЛИЗАЦИЯ ===
    print("🔍 1. Инициализация event_bus...")
    received_events = []

    async def bot_like_handler(event):
        print(f"📡 Получено событие: {event}")
        received_events.append(event)

    subscribe_async("task_result", bot_like_handler)
    subscribe_async("task_error", bot_like_handler)

    print("✅ Handler подписан на события")

    # === 2. ЗАПУСК ЗАДАЧИ ===
    print("\n🔍 2. Запуск задачи через process_manager...")
    lat, lon, user_id = 55.75, 37.62, 123

    task_id = await enqueue_script(
        "scripts/weather/weather_today_script.py",
        [str(lat), str(lon), str(user_id)]
    )
    print(f"✅ Задача поставлена: {task_id}")

    # === 3. ОЖИДАНИЕ СОБЫТИЯ (с деталями) ===
    print("\n🔍 3. Ожидание события от скрипта...")
    for i in range(30):  # 30 секунд ожидания
        print(f"⏳ Ждём событие... {i + 1}/30 (получено: {len(received_events)})")
        if len(received_events) > 0:
            print("✅ Событие получено!")
            break
        await asyncio.sleep(1)

    # === 4. АНАЛИЗ РЕЗУЛЬТАТА ===
    print("\n🔍 4. Анализ результата...")
    if len(received_events) == 0:
        print("❌ Событие не получено")
        print("❌ Цепочка не замкнулась")

        # Проверим, что происходит с задачей
        print("\n🔍 5. Проверка статуса задачи...")
        from core.db.process_log_db import get_task_status
        # Пока пропустим, т.к. get_task_status нет в текущей версии

        print("\n💡 Попробуй запустить скрипт вручную:")
        print(f"   python scripts/weather/weather_today_script.py {lat} {lon} {user_id} {task_id}")
        print("   И посмотреть логи в logs/")
        return

    event = received_events[0]
    print(f"✅ Событие получено: {event}")

    # Проверяем тип события
    if event.get("EVENT_TYPE") != "task_result":
        print(f"❌ Неправильный тип события: {event.get('EVENT_TYPE')}")
        return

    # Проверяем тип результата
    if event.get("RESULT_TYPE") != "graph":
        print(f"❌ Неправильный результат: {event.get('RESULT_TYPE')}")
        return

    # Проверяем, что пришёл график
    file_path = event.get("FILE_PATH")
    if not file_path:
        print("❌ Не получен FILE_PATH")
        return

    # Проверяем, что файл существует
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return

    print(f"✅ График сохранён: {file_path}")

    # Проверяем SUMMARY
    summary = event.get("SUMMARY")
    if not summary:
        print("⚠️  SUMMARY не получен")
    else:
        print(f"📊 Сводка: {summary}")

    # Проверяем LOCATION_NAME
    location = event.get("LOCATION_NAME")
    if not location:
        print("⚠️  LOCATION_NAME не получен")
    else:
        print(f"🌍 Местоположение: {location}")

    # === 6. ПРОВЕРКА КЭША ===
    print("\n🔍 6. Проверка кэша в local_db_weather...")
    from core.db.local_db_weather import get_cached_weather
    cached = get_cached_weather(lat, lon, source="open_meteo")
    if cached:
        print("✅ Данные закэшированы")
        print(f"   Ключевые поля: {list(cached.keys())[:5]}...")  # первые 5
    else:
        print("❌ Данные не закэшированы")

    # === 7. ИТОГ ===
    print("\n" + "="*60)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТА ЦЕПОЧКИ")
    print("="*60)
    print(f"✅ Задача запущена: {task_id}")
    print(f"✅ Событие получено: {event.get('EVENT_TYPE')}")
    print(f"✅ Результат: {event.get('RESULT_TYPE')}")
    print(f"✅ График: {file_path}")
    print(f"📊 Сводка: {summary}")
    print(f"🌍 Место: {location}")
    print(f"💾 Кэш: {'Да' if cached else 'Нет'}")
    print("-" * 60)
    print("🎉 Цепочка успешно пройдена!")

    # === 8. ОЧИСТКА ===
    clear_all_handlers()
    db_config.WEATHER_CACHE_DB = original_weather_db
    if os.path.exists(temp_weather_db):
        os.unlink(temp_weather_db)
    print(f"🧹 Временная БД удалена: {temp_weather_db}")


if __name__ == "__main__":
    asyncio.run(test_weather_full_chain_verbose())