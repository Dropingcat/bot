# -*- coding: utf-8 -*-
"""
Тесты для проверки валидации входных данных api_client.py
"""

import asyncio
from core.utils.api_client import APIClient

def test_input_validation():
    print("🧪 Тест: Валидация входных данных api_client")
    client = APIClient()
    results = []

    # === 1. Правильный одиночный запрос ===
    print("\n🔍 Тест 1: Правильные координаты (lat, lon)")
    try:
        valid = client.validate_input(lat=55.75, lon=37.62)
        if valid:
            print("✅ OK: Валидация прошла")
            results.append(("Одиночный запрос", True, "OK"))
        else:
            print("❌ Ошибка валидации")
            results.append(("Одиночный запрос", False, "Validation failed"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Одиночный запрос", False, str(e)))

    # === 2. Правильный диапазон ===
    print("\n🔍 Тест 2: Правильный диапазон (start, end, step)")
    try:
        valid = client.validate_input(
            start_lat=55.0, start_lon=37.0,
            end_lat=56.0, end_lon=38.0,
            step_deg=0.25
        )
        if valid:
            print("✅ OK: Валидация прошла")
            results.append(("Диапазон", True, "OK"))
        else:
            print("❌ Ошибка валидации")
            results.append(("Диапазон", False, "Validation failed"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Диапазон", False, str(e)))

    # === 3. Неправильные координаты (за границами) ===
    print("\n🔍 Тест 3: Неправильные координаты (lat > 90)")
    try:
        valid = client.validate_input(lat=99.0, lon=37.62)
        if not valid:
            print("✅ OK: Ошибка корректно обнаружена")
            results.append(("Неправильные координаты", True, "OK"))
        else:
            print("❌ Валидация не сработала")
            results.append(("Неправильные координаты", False, "Validation passed"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Неправильные координаты", False, str(e)))

    # === 4. Неправильный шаг ===
    print("\n🔍 Тест 4: Неправильный шаг (<= 0)")
    try:
        valid = client.validate_input(
            start_lat=55.0, start_lon=37.0,
            end_lat=56.0, end_lon=38.0,
            step_deg=-0.1
        )
        if not valid:
            print("✅ OK: Ошибка шага корректно обнаружена")
            results.append(("Неправильный шаг", True, "OK"))
        else:
            print("❌ Валидация не сработала")
            results.append(("Неправильный шаг", False, "Validation passed"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Неправильный шаг", False, str(e)))

    # === 5. Смешанные параметры (одиночный + диапазон) ===
    print("\n🔍 Тест 5: Смешанные параметры (lat и start_lat)")
    try:
        valid = client.validate_input(
            lat=55.75, lon=37.62,
            start_lat=55.0, start_lon=37.0,
            end_lat=56.0, end_lon=38.0,
            step_deg=0.25
        )
        if not valid:
            print("✅ OK: Ошибка смешивания параметров обнаружена")
            results.append(("Смешанные параметры", True, "OK"))
        else:
            print("❌ Валидация не сработала")
            results.append(("Смешанные параметры", False, "Validation passed"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Смешанные параметры", False, str(e)))

    # === 6. Пустой ввод ===
    print("\n🔍 Тест 6: Пустой ввод (никакие параметры не заданы)")
    try:
        valid = client.validate_input()
        if not valid:
            print("✅ OK: Ошибка пустого ввода обнаружена")
            results.append(("Пустой ввод", True, "OK"))
        else:
            print("❌ Валидация не сработала")
            results.append(("Пустой ввод", False, "Validation passed"))
    except Exception as e:
        print(f"❌ Исключение: {e}")
        results.append(("Пустой ввод", False, str(e)))

    # === Отчёт ===
    print("\n" + "="*60)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ВАЛИДАЦИИ")
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
        print("🎉 Все тесты валидации пройдены успешно!")
    else:
        print("⚠️  Некоторые тесты не прошли. Проверьте логи выше.")


if __name__ == "__main__":
    test_input_validation()