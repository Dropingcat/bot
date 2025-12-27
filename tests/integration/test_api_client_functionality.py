# -*- coding: utf-8 -*-
"""
Интеграционный тест: api_client.py — запросы с разными параметрами и моделями
"""

import asyncio
from core.utils.api_client import APIClient

def test_api_client_functionality():
    print("🧪 Тест: api_client — запросы с разными параметрами и моделями")
    client = APIClient()
    results = []

    # === 1. Одна точка: 55.0, 37.0 — только температура 2 м ===
    print("\n🔍 Тест 1: Одна точка (55.0, 37.0) — температура 2 м")
    try:
        # Используем open_meteo, но вручную фильтруем данные
        data = client.get_weather_data(55.0, 37.0, "open_meteo", days=1)
        if data and "hourly" in data and "temperature_2m" in data["hourly"]:
            print("✅ OK: Температура 2 м получена")
            results.append(("Одна точка", True, "OK"))
        else:
            print("❌ Ошибка: температура не получена")
            results.append(("Одна точка", False, "No temp data"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Одна точка", False, str(e)))

    # === 2. Диапазон: 55.5, 37.5 → 56.0, 38.0 — температура + влажность ===
    print("\n🔍 Тест 2: Диапазон (55.5, 37.5) → (56.0, 38.0) — темп + влажность")
    try:
        results_range = asyncio.run(
            client.get_weather_range(
                start_lat=55.5, start_lon=37.5,
                end_lat=56.0, end_lon=38.0,
                step_deg=0.25, provider="open_meteo", days=1
            )
        )
        # Проверим, что хотя бы одна точка вернула данные
        success_points = [k for k, v in results_range.items() if v is not None]
        if len(success_points) > 0:
            # Проверим, что в данных есть нужные параметры
            sample_data = results_range[success_points[0]]
            has_temp = "hourly" in sample_data and "temperature_2m" in sample_data["hourly"]
            has_humidity = "hourly" in sample_data and "relative_humidity_2m" in sample_data["hourly"]
            if has_temp and has_humidity:
                print(f"✅ OK: {len(success_points)} точек получили темп + влажность")
                results.append(("Диапазон", True, "OK"))
            else:
                print("❌ Ошибка: нет темп или влажности в данных")
                results.append(("Диапазон", False, "Missing temp/humidity"))
        else:
            print("❌ Ошибка: диапазон не вернул данных")
            results.append(("Диапазон", False, "No data"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Диапазон", False, str(e)))

    # === 3. Варьирование моделей ===
    print("\n🔍 Тест 3: Варьирование моделей (open_meteo, gfs, ecmwf)")
    models = ["open_meteo", "gfs", "ecmwf"]
    models_results = []
    for model in models:
        print(f"   🔄 Проверка {model}...")
        try:
            data = client.get_weather_data(55.0, 37.0, model, days=1)
            if data:
                print(f"   ✅ {model}: OK")
                models_results.append((model, True))
            else:
                print(f"   ❌ {model}: Нет данных")
                models_results.append((model, False))
        except Exception as e:
            print(f"   ❌ {model}: Ошибка: {e}")
            models_results.append((model, False))

    # Подсчёт
    models_passed = sum(1 for _, success in models_results if success)
    print(f"   ✅ Успешно: {models_passed}/{len(models)} моделей")
    results.append(("Модели", models_passed > 0, f"{models_passed}/{len(models)} OK"))

    # === 4. Вариант: температура + влажность + давление ===
    print("\n🔍 Тест 4: Точка (55.75, 37.62) — температура, влажность, давление")
    try:
        data = client.get_weather_data(55.75, 37.62, "open_meteo", days=1)
        if data:
            has_temp = "hourly" in data and "temperature_2m" in data["hourly"]
            has_humidity = "hourly" in data and "relative_humidity_2m" in data["hourly"]
            has_pressure = "hourly" in data and "pressure_msl" in data["hourly"]
            if has_temp and has_humidity and has_pressure:
                print("✅ OK: Все 3 параметра (T, RH, P) получены")
                results.append(("3 параметра", True, "OK"))
            else:
                print("❌ Ошибка: не все параметры получены")
                results.append(("3 параметра", False, "Missing params"))
        else:
            print("❌ Ошибка: данные не получены")
            results.append(("3 параметра", False, "No data"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("3 параметра", False, str(e)))

    # === 5. Диапазон с меньшим шагом (0.1) ===
    print("\n🔍 Тест 5: Диапазон (55.0, 37.0) → (55.2, 37.2), step=0.1")
    try:
        results_range = asyncio.run(
            client.get_weather_range(
                start_lat=55.0, start_lon=37.0,
                end_lat=55.2, end_lon=37.2,
                step_deg=0.1, provider="open_meteo", days=1
            )
        )
        success_points = [k for k, v in results_range.items() if v is not None]
        if len(success_points) > 0:
            print(f"✅ OK: {len(success_points)} точек получили (step=0.1)")
            results.append(("Диапазон 0.1", True, "OK"))
        else:
            print("❌ Ошибка: диапазон (step=0.1) не вернул данных")
            results.append(("Диапазон 0.1", False, "No data"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Диапазон 0.1", False, str(e)))

    # === Отчёт ===
    print("\n" + "="*60)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ API_CLIENT ФУНКЦИОНАЛЬНОСТИ")
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
        print("🎉 Все функциональные тесты пройдены успешно!")
    else:
        print("⚠️  Некоторые тесты не прошли. Проверьте логи выше.")

    # Отдельный отчёт по моделям
    print("\n📊 Результаты по моделям:")
    for model, success in models_results:
        status = "✅" if success else "❌"
        print(f"   {status} {model}")


if __name__ == "__main__":
    test_api_client_functionality()