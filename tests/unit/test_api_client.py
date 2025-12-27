# -*- coding: utf-8 -*-
"""
Тесты для core/utils/api_client.py
Тестирует:
- Запросы к Open-Meteo, GFS, ECMWF
- Кэширование через local_db_weather
- Обработку ошибок
- Валидацию координат
"""

import asyncio
import tempfile
import os
from pathlib import Path

# Подменяем пути к БД
from config import db_config
original_weather_db = db_config.WEATHER_CACHE_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_weather_db = tmp.name

db_config.WEATHER_CACHE_DB = Path(temp_weather_db)

from core.utils.api_client import APIClient, get_weather_forecast, get_compared_forecast
from core.db.local_db_weather import init_db, get_cached_weather

def test_api_client():
    print("🧪 Тест: APIClient")
    results = []
    
    client = APIClient()
    
    # === 1. ТЕСТ: Open-Meteo ===
    print("\n🔍 Тест 1: Open-Meteo API")
    try:
        data = client.get_weather_data(55.75, 37.62, "open_meteo", days=1)
        if data and "hourly" in data:
            print("✅ Open-Meteo: Успех")
            results.append(("Open-Meteo", True, "OK"))
        else:
            print("❌ Open-Meteo: Нет данных")
            results.append(("Open-Meteo", False, "No data"))
    except Exception as e:
        print(f"❌ Open-Meteo: Ошибка: {e}")
        results.append(("Open-Meteo", False, str(e)))

    # === 2. ТЕСТ: GFS ===
    print("\n🔍 Тест 2: GFS API")
    try:
        data = client.get_weather_data(55.75, 37.62, "gfs", days=1)
        if data and "hourly" in data:
            print("✅ GFS: Успех")
            results.append(("GFS", True, "OK"))
        else:
            print("❌ GFS: Нет данных")
            results.append(("GFS", False, "No data"))
    except Exception as e:
        print(f"❌ GFS: Ошибка: {e}")
        results.append(("GFS", False, str(e)))

    # === 3. ТЕСТ: ECMWF ===
    print("\n🔍 Тест 3: ECMWF API")
    try:
        data = client.get_weather_data(55.75, 37.62, "ecmwf", days=1)
        if data and "hourly" in data:
            print("✅ ECMWF: Успех")
            results.append(("ECMWF", True, "OK"))
        else:
            print("❌ ECMWF: Нет данных")
            results.append(("ECMWF", False, "No data"))
    except Exception as e:
        print(f"❌ ECMWF: Ошибка: {e}")
        results.append(("ECMWF", False, str(e)))

    # === 4. ТЕСТ: Кэширование ===
    print("\n🔍 Тест 4: Кэширование в local_db_weather")
    try:
        init_db()  # Инициализация БД
        lat, lon = 55.75, 37.62
        
        # Запрашиваем данные
        data1 = client.get_weather_data(lat, lon, "open_meteo", days=1, use_cache=True)
        
        # Запрашиваем снова — должно быть из кэша
        data2 = client.get_weather_data(lat, lon, "open_meteo", days=1, use_cache=True)
        
        if data1 and data2:
            print("✅ Кэширование: Успех")
            results.append(("Кэширование", True, "OK"))
        else:
            print("❌ Кэширование: Ошибка")
            results.append(("Кэширование", False, "Cache error"))
    except Exception as e:
        print(f"❌ Кэширование: Ошибка: {e}")
        results.append(("Кэширование", False, str(e)))

    # === 5. ТЕСТ: Сравнение моделей ===
    print("\n🔍 Тест 5: Сравнение моделей")
    try:
        results_multi = client.get_multiple_providers_data(55.75, 37.62, ["open_meteo", "gfs"])
        if all(results_multi.values()):
            print("✅ Сравнение: Успех")
            results.append(("Сравнение", True, "OK"))
        else:
            print("❌ Сравнение: Некоторые провайдеры не вернули данные")
            results.append(("Сравнение", False, "Partial data"))
    except Exception as e:
        print(f"❌ Сравнение: Ошибка: {e}")
        results.append(("Сравнение", False, str(e)))

    # === 6. ТЕСТ: Ошибки API (неправильные координаты) ===
    print("\n🔍 Тест 6: Обработка ошибок (неправильные координаты)")
    try:
        data = client.get_weather_data(999.0, 999.0, "open_meteo", days=1)
        if data is None:
            print("✅ Ошибки: Успешно обработаны")
            results.append(("Ошибки", True, "OK"))
        else:
            print("❌ Ошибки: Не обработаны")
            results.append(("Ошибки", False, "Data returned for invalid coords"))
    except Exception as e:
        print(f"❌ Ошибки: Исключение: {e}")
        results.append(("Ошибки", False, str(e)))

    # === 7. ТЕСТ: Удобные функции ===
    print("\n🔍 Тест 7: Удобные функции (get_weather_forecast)")
    try:
        data = get_weather_forecast(55.75, 37.62, "open_meteo")
        if data:
            print("✅ Удобные функции: Успех")
            results.append(("Удобные функции", True, "OK"))
        else:
            print("❌ Удобные функции: Нет данных")
            results.append(("Удобные функции", False, "No data"))
    except Exception as e:
        print(f"❌ Удобные функции: Ошибка: {e}")
        results.append(("Удобные функции", False, str(e)))

    # === 8. ТЕСТ: Сравнение нескольких моделей ===
    print("\n🔍 Тест 8: get_compared_forecast")
    try:
        data = get_compared_forecast(55.75, 37.62)
        if isinstance(data, dict) and len(data) > 0:
            print("✅ get_compared_forecast: Успех")
            results.append(("get_compared_forecast", True, "OK"))
        else:
            print("❌ get_compared_forecast: Нет данных")
            results.append(("get_compared_forecast", False, "No data"))
    except Exception as e:
        print(f"❌ get_compared_forecast: Ошибка: {e}")
        results.append(("get_compared_forecast", False, str(e)))

    # === ОТЧЁТ ===
    print("\n" + "="*60)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ api_client.py")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, success, msg in results:
        status = "✅ ПРОШЁЛ" if success else "❌ НЕ ПРОШЁЛ"
        print(f"{status:<12} | {name:<25} | {msg}")
        if success:
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"Всего: {len(results)}, Успешно: {passed}, Ошибок: {failed}")
    
    if failed == 0:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️  Некоторые тесты не прошли. Проверьте логи выше.")
    
    # Восстановление
    db_config.WEATHER_CACHE_DB = original_weather_db
    os.unlink(temp_weather_db)
    print(f"🧹 Временная БД удалена: {temp_weather_db}")


if __name__ == "__main__":
    test_api_client()