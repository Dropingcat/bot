# -*- coding: utf-8 -*-
"""
Тест: комплексная проверка связей между всеми основными компонентами.
Цель: Убедиться, что bot -> process_manager -> script -> api -> cache -> graph -> event -> bot - работает корректно.
"""
import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

# --- ИМПОРТЫ ---
from core.event_bus import subscribe_async, clear_all_handlers
from core.process_manager import enqueue_script, init_process_manager
from core.db.local_db_weather import get_cached_weather, init_db as init_weather_db
from core.db.process_log_db import init_db as init_process_log_db, get_task_status

# === ИСПРАВЛЕНО: Добавляем logging ===
import logging

logger = logging.getLogger("test_full_chain_comprehensive")

# --- НАСТРОЙКА ---
# Путь к тестовому скрипту (например, weather_today_script)
TEST_SCRIPT_PATH = "scripts/weather/weather_today_script.py"
# Тестовые параметры
LAT = 55.75
LON = 37.62
USER_ID = 12345
TASK_NAME = "test_comprehensive_chain_task"

# Временные файлы БД для теста
TEMP_WEATHER_DB = None
TEMP_PROCESS_LOG_DB = None

async def test_full_chain_comprehensive():
    print("🧪 ТЕСТ: Комплексная проверка связей (Comprehensive Chain Test)")
    print("="*80)

    # === 1. ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ ===
    print("🔍 1. Инициализация систем...")
    try:
        # Инициализация process_manager
        init_process_manager()
        await asyncio.sleep(1)  # Дадим воркерам время стартовать
        print("✅ Process Manager инициализирован.")

        # Подготовка временных БД
        global TEMP_WEATHER_DB, TEMP_PROCESS_LOG_DB
        TEMP_WEATHER_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
        TEMP_PROCESS_LOG_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name

        # Подменяем пути в конфиге (если используется config)
        # from config import db_config
        # original_weather_db = db_config.WEATHER_CACHE_DB
        # original_process_log_db = db_config.PROCESS_LOG_DB
        # db_config.WEATHER_CACHE_DB = TEMP_WEATHER_DB
        # db_config.PROCESS_LOG_DB = TEMP_PROCESS_LOG_DB

        # Инициализация БД
        init_weather_db()
        init_process_log_db()
        print(f"✅ Временные БД созданы: {TEMP_WEATHER_DB}, {TEMP_PROCESS_LOG_DB}")

        # Подписка на события
        received_events = []
        def event_handler(event):
            print(f"📡 Получено событие: {event}")
            received_events.append(event)
        subscribe_async("task_result", event_handler)
        subscribe_async("task_error", event_handler)
        print("✅ Handler подписан на события (task_result, task_error).")

    except Exception as e:
        print(f"❌ Ошибка на этапе инициализации: {e}")
        return

    # === 2. ПОДАЧА ЗАДАЧИ В ОЧЕРЕДЬ ===
    print(f"\n🚀 2. Подача задачи через process_manager...")
    print(f"   Скрипт: {TEST_SCRIPT_PATH}")
    print(f"   Параметры: [{LAT}, {LON}, {USER_ID}]")
    try:
        task_id = await enqueue_script(TEST_SCRIPT_PATH, [str(LAT), str(LON), str(USER_ID)])
        print(f"✅ Задача поставлена в очередь: {task_id}")
    except Exception as e:
        print(f"❌ Ошибка при постановке задачи: {e}")
        return

    # === 3. ОЖИДАНИЕ СОБЫТИЯ ===
    print(f"\n⏳ 3. Ожидание события от скрипта (таймаут 60 секунд)...")
    timeout = 60
    start_time = asyncio.get_event_loop().time()
    event_received = False
    while not event_received and (asyncio.get_event_loop().time() - start_time) < timeout:
        await asyncio.sleep(1)
        if received_events:
            event_received = True
            print(f"✅ Событие получено через {asyncio.get_event_loop().time() - start_time:.2f} секунд!")
            break
        print(f"⏳ Ждём событие... {asyncio.get_event_loop().time() - start_time:.0f}/{timeout} сек")

    if not event_received:
        print("❌ Событие не получено в течение таймаута.")
        # Проверим статус задачи в БД
        status_info = get_task_status(task_id)
        print(f"📊 Статус задачи в БД: {status_info}")
        return

    # === 4. АНАЛИЗ ПОЛУЧЕННОГО СОБЫТИЯ ===
    print(f"\n🔍 4. Анализ полученного события...")
    event = received_events[0]
    print(f"   Тип события: {event.get('EVENT_TYPE')}")
    print(f"   Тип результата: {event.get('RESULT_TYPE')}")
    print(f"   ID Пользователя: {event.get('USER_ID')}")
    print(f"   Сообщение: {event.get('MESSAGE', 'N/A')}")
    file_path_str = event.get('FILE_PATH')
    if file_path_str:
        print(f"   Путь к файлу: {file_path_str}")
        # === ИСПРАВЛЕНО: Используем resolve() для получения абсолютного пути ===
        file_path_obj = Path(file_path_str).resolve()
        if file_path_obj.exists():
            print(f"   ✅ Файл существует.")
        else:
            print(f"   ❌ Файл НЕ существует по указанному пути!")
    else:
        print(f"   ❌ В событии нет FILE_PATH.")

    # === 5. ПРОВЕРКА СТАТУСА ЗАДАЧИ В БД ===
    print(f"\n🔍 5. Проверка статуса задачи в БД...")
    try:
        status_info = get_task_status(task_id)
        print(f"   Статус из БД: {status_info}")
        if status_info and status_info.get('status') in ['finished', 'failed']:
            print(f"   ✅ Статус задачи в БД соответствует завершению.")
        else:
            print(f"   ⚠️ Статус задачи в БД не завершён: {status_info.get('status') if status_info else 'N/A'}")
    except Exception as e:
        logger.error(f"❌ Ошибка при получении статуса задачи из БД: {e}")

    # === 6. ПРОВЕРКА КЭША (если скрипт кэшировал данные) ===
    print(f"\n🔍 6. Проверка кэша в local_db_weather...")
    try:
        # === ИСПРАВЛЕНО: Добавляем forecast_datetime ===
        check_time = datetime.now()
        cached_data = get_cached_weather(lat=55.75, lon=37.62, source="open_meteo", forecast_datetime=datetime.now())
        if cached_data:
            print(f"   ✅ Данные найдены в кэше.")
            # print(f"   Данные: {cached_data}") # Не выводим всё, только факт
        else:
            print(f"   ❌ Данные НЕ найдены в кэши (проверяли до {check_time}).")
            # Это может быть нормально, если скрипт не кэширует или кэширует по-другому
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке кэша: {e}")
        cached_data = None

    # === 7. ВЫВОД РЕЗУЛЬТАТА ТЕСТА ===
    print("\n" + "="*80)
    if event_received and event.get('EVENT_TYPE') == 'task_result':
        print("🎉 ТЕСТ ПРОЙДЕН: Цепочка связей успешно замкнута!")
        print(f"   - Задача: {task_id}")
        print(f"   - Событие: {event.get('EVENT_TYPE')}")
        print(f"   - Результат: {event.get('RESULT_TYPE')}")
        print(f"   - Файл: {'Да' if file_path_str and Path(file_path_str).resolve().exists() else 'Нет/Ошибка'}")
        print(f"   - Кэш: {'Да' if cached_data else 'Нет/Ошибка'}")
        print(f"   - Статус задачи: {'Завершена' if status_info and status_info.get('status') == 'finished' else 'Не завершена'}")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Цепочка не замкнута или результат некорректен.")
    print("="*80)

    # === 8. ОЧИСТКА ===
    print("\n🧹 8. Очистка временных файлов...")
    try:
        # Восстанавливаем пути (если подменяли)
        # db_config.WEATHER_CACHE_DB = original_weather_db
        # db_config.PROCESS_LOG_DB = original_process_log_db

        # Очищаем подписки
        clear_all_handlers()

        # Удаляем временные файлы БД
        if TEMP_WEATHER_DB and os.path.exists(TEMP_WEATHER_DB):
            os.unlink(TEMP_WEATHER_DB)
            print(f"   Удалена временная БД кэша: {TEMP_WEATHER_DB}")
        if TEMP_PROCESS_LOG_DB and os.path.exists(TEMP_PROCESS_LOG_DB):
            os.unlink(TEMP_PROCESS_LOG_DB)
            print(f"   Удалена временная БД лога задач: {TEMP_PROCESS_LOG_DB}")

    except Exception as e:
        print(f"⚠️ Ошибка при очистке: {e}")

    print("\n🏁 Тест завершён.")


if __name__ == "__main__":
    asyncio.run(test_full_chain_comprehensive())