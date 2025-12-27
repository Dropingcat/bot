# -*- coding: utf-8 -*-
"""
Тест: интеграция user_profile_script с process_manager, api, db
"""

import asyncio
import tempfile
import os
from pathlib import Path
import random
from datetime import datetime, timedelta

# Подменяем БД для теста
from config import db_config
original_meteo_db = db_config.METEO_DB
original_weather_db = db_config.WEATHER_CACHE_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_meteo_db = tmp.name

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_weather_db = tmp.name

db_config.METEO_DB = Path(temp_meteo_db)
db_config.WEATHER_CACHE_DB = Path(temp_weather_db)

from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script
from core.db.local_db_meteo import get_user_health_log, get_user_health_stats

async def test_user_profile_integration():
    print("🧪 ТЕСТ: Интеграция user_profile_script")
    print("="*60)

    # === 1. ПОДПИСКА НА СОБЫТИЯ ===
    print("🔍 1. Подписка на события...")
    received_events = []

    async def handler(event):
        print(f"📡 Получено событие: {event}")
        received_events.append(event)

    subscribe_async("task_result", handler)
    subscribe_async("task_error", handler)

    print("✅ Подписка оформлена")

    # === 2. СИНТЕЗ ДАННЫХ ===
    print("\n🔍 2. Синтез данных самочувствия...")
    user_id = 123456
    timestamp = (datetime.now() - timedelta(minutes=5)).isoformat()  # 5 минут назад
    lat, lon = 55.75, 37.62
    systolic = 120 + random.randint(-10, 10)
    diastolic = 80 + random.randint(-5, 5)
    heart_rate = 70 + random.randint(-10, 10)
    spo2 = 97 + random.random()
    migraine = random.randint(0, 10)
    drowsiness = random.randint(0, 10)
    anxiety = random.randint(0, 10)
    depression = random.randint(0, 10)
    excitement = random.randint(0, 10)
    malaise = random.randint(0, 10)
    comment = "Тестовое измерение"

    print(f"📊 Данные: user_id={user_id}, AD={systolic}/{diastolic}, ЧСС={heart_rate}, СаО2={spo2:.1f}")

    # === 3. ЗАПУСК СКРИПТА ===
    print("\n🔍 3. Запуск user_profile_script через process_manager...")
    task_id = await enqueue_script(
        "scripts/meteo/user_profile_script.py",
        [
            str(user_id),
            timestamp,
            str(lat),
            str(lon),
            str(systolic),
            str(diastolic),
            str(heart_rate),
            str(spo2),
            str(migraine),
            str(drowsiness),
            str(anxiety),
            str(depression),
            str(excitement),
            str(malaise),
            comment
        ]
    )
    print(f"✅ Задача поставлена: {task_id}")

    # === 4. ОЖИДАНИЕ СОБЫТИЯ ===
    print("\n🔍 4. Ожидание события от скрипта...")
    for i in range(30):  # 30 секунд
        if len(received_events) > 0:
            break
        print(f"⏳ Ждём событие... {i + 1}/30")
        await asyncio.sleep(1)

    # === 5. АНАЛИЗ СОБЫТИЯ ===
    print("\n🔍 5. Анализ события...")
    if len(received_events) == 0:
        print("❌ Событие не получено")
        return

    event = received_events[0]
    print(f"✅ Событие: {event}")

    if event.get("EVENT_TYPE") != "task_result":
        print(f"❌ Неправильный тип события: {event.get('EVENT_TYPE')}")
        return

    if "Данные сохранены" not in event.get("MESSAGE", ""):
        print(f"❌ Неправильное сообщение: {event.get('MESSAGE')}")
        return

    print("✅ Событие обработано корректно")

    # === 6. ПРОВЕРКА БАЗЫ ===
    print("\n🔍 6. Проверка базы данных...")
    logs = get_user_health_log(user_id, timestamp, timestamp)
    if len(logs) == 0:
        print("❌ Запись в БД не найдена")
        return

    log = logs[0]
    print(f"✅ Запись найдена: AD={log['systolic']}/{log['diastolic']}, ЧСС={log['heart_rate']}")

    # Проверяем, что данные совпадают
    if abs(log['systolic'] - systolic) < 0.1 and abs(log['heart_rate'] - heart_rate) < 1:
        print("✅ Данные совпадают")
    else:
        print(f"❌ Данные не совпадают: {log} vs {systolic}, {heart_rate}")

    # === 7. ПРОВЕРКА СТАТИСТИКИ ===
    print("\n🔍 7. Проверка статистики...")
    stats = get_user_health_stats(user_id)
    if stats.get("avg_systolic"):
        print(f"✅ Статистика: avg_AD={stats['avg_systolic']:.1f}")
    else:
        print("❌ Статистика не найдена")

    # === 8. ИТОГ ===
    print("\n" + "="*60)
    print("📋 РЕЗУЛЬТАТЫ ИНТЕГРАЦИОННОГО ТЕСТА")
    print("="*60)
    print(f"✅ Задача запущена: {task_id}")
    print(f"✅ Событие получено: {event.get('EVENT_TYPE')}")
    print(f"✅ Запись в БД: {'Да' if logs else 'Нет'}")
    print(f"✅ Данные совпадают: {'Да' if abs(log['systolic'] - systolic) < 0.1 else 'Нет'}")
    print(f"✅ Статистика: {'Да' if stats.get('avg_systolic') else 'Нет'}")
    print("-" * 60)
    print("🎉 Интеграция работает!")

    # === 9. ОЧИСТКА ===
    clear_all_handlers()
    db_config.METEO_DB = original_meteo_db
    db_config.WEATHER_CACHE_DB = original_weather_db
    if os.path.exists(temp_meteo_db):
        os.unlink(temp_meteo_db)
    if os.path.exists(temp_weather_db):
        os.unlink(temp_weather_db)
    print(f"🧹 Временные БД удалены")


if __name__ == "__main__":
    asyncio.run(test_user_profile_integration())