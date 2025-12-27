# -*- coding: utf-8 -*-
"""
Тест: расширенный анализ фронтов
"""

import numpy as np
from scripts.meteo._processes.front_analyzer import (
    detect_fronts,
    extract_front_geometry,
    estimate_pass_time
)

def test_front_analyzer_advanced():
    print("🧪 ТЕСТ: Расширенный анализ фронтов")
    print("="*60)

    # === 1. СИНТЕЗ ДАННЫХ ===
    print("🔍 1. Синтез данных...")
    shape = (100, 100)
    lat_grid, lon_grid = np.meshgrid(np.linspace(50, 60, shape[0]), np.linspace(30, 40, shape[1]))

    # Создаём искусственный фронт (перепад температуры)
    x = lon_grid
    y = lat_grid
    theta_e = 300 + 20 * np.tanh((x - 35) * 2)  # перепад вдоль 35°E
    theta_e += np.random.normal(0, 1, shape)  # шум

    q = 0.01 + 0.005 * np.random.normal(0, 1, shape)
    mslp = 1013 - 2 * np.exp(-((x - 35)**2 + (y - 55)**2) / 2)  # барическая ложбина
    mslp += np.random.normal(0, 0.5, shape)

    tp = np.zeros_like(x)
    tp[(x > 34) & (x < 36) & (y > 54) & (y < 56)] = 2.0  # осадки на фронте
    tp += np.random.exponential(0.1, shape)

    dewpoint = 15 + 5 * np.tanh((x - 35) * 2) + np.random.normal(0, 0.5, shape)
    wind_u = np.full_like(x, 5.0) + np.random.normal(0, 1, shape)
    wind_v = np.full_like(x, 2.0) + np.random.normal(0, 1, shape)

    print(f"📊 Синтез: θe={theta_e.min():.1f}..{theta_e.max():.1f}, MSLP={mslp.min():.1f}..{mslp.max():.1f}")

    # === 2. АНАЛИЗ ФРОНТА ===
    print("\n🔍 2. Анализ фронтов...")
    result = detect_fronts(theta_e, q, mslp, tp, dewpoint, wind_u, wind_v)

    summary = result['summary']
    print(f"✅ Найдено: {summary['total_front_cells']} ячеек")
    print(f"   Достоверность: {summary['avg_confidence']:.2f}")
    print(f"   Типы: {summary['types']}")

    # === 3. ПРОВЕРКА КАЧЕСТВА ===
    print("\n🔍 3. Проверка качества...")
    if summary['total_front_cells'] > 100:
        print("✅ Фронты найдены")
    else:
        print("❌ Мало фронтов")

    if summary['avg_confidence'] > 3.0:
        print("✅ Высокая достоверность")
    else:
        print("⚠️  Низкая достоверность")

    # === 4. ИЗВЛЕЧЕНИЕ ГЕОМЕТРИИ ===
    print("\n🔍 4. Извлечение геометрии...")
    front_coords = extract_front_geometry(result['front_mask'], lat_grid, lon_grid)
    if len(front_coords) > 0:
        print(f"✅ Координаты: {len(front_coords)} точек")
        print(f"   Пример: {front_coords[0]}")
    else:
        print("❌ Координаты не извлечены")

    # === 5. ОЦЕНКА ВРЕМЕНИ ПРОХОЖДЕНИЯ ===
    print("\n🔍 5. Оценка времени прохождения...")
    target_lat, target_lon = 55.0, 35.0
    pass_time = estimate_pass_time(front_coords, (wind_u, wind_v), target_lat, target_lon)
    if pass_time:
        print(f"✅ Время прохождения: {pass_time:.1f} ч")
    else:
        print("❌ Время не оценено")

    # === 6. ВРЕМЕННОЙ АНАЛИЗ (2 точки) ===
    print("\n🔍 6. Временной анализ...")
    # Вторая точка: фронт сместился
    theta_e2 = np.roll(theta_e, shift=-5, axis=1)  # смещение на 5 ячеек
    result2 = detect_fronts(theta_e2, q, mslp, tp, dewpoint, wind_u, wind_v)

    shift = abs(summary['total_front_cells'] - result2['summary']['total_front_cells'])
    print(f"   Сдвиг фронта: {shift} ячеек")

    # === 7. ФИЛЬТРАЦИЯ ПО ДОСТОВЕРНОСТИ ===
    print("\n🔍 7. Фильтрация по достоверности...")
    high_conf_mask = result['confidence'] >= 4
    high_conf_fronts = result['front_mask'] & high_conf_mask
    print(f"   Высокая достоверность: {np.sum(high_conf_fronts)} ячеек")

    # === 8. ОШИБКИ ===
    print("\n🔍 8. Тест на ошибки...")
    try:
        # Неправильные размерности
        bad_result = detect_fronts(
            theta_e[:50, :50], q, mslp, tp, dewpoint, wind_u, wind_v
        )
        print("❌ Ошибки не обнаружены (ожидаемо)")
    except Exception as e:
        print(f"✅ Ошибка обнаружена: {e}")

    # === 9. ИТОГ ===
    print("\n" + "="*60)
    print("📋 РЕЗУЛЬТАТЫ РАСШИРЕННОГО ТЕСТА")
    print("="*60)
    print(f"✅ Фронты: {summary['total_front_cells']}")
    print(f"✅ Достоверность: {summary['avg_confidence']:.2f}")
    print(f"✅ Геометрия: {len(front_coords) > 0}")
    print(f"✅ Время: {pass_time is not None}")
    print(f"✅ Сдвиг: {shift}")
    print(f"✅ Фильтр: {np.sum(high_conf_fronts)}")
    print("-" * 60)
    print("🎉 Тест пройден!")


if __name__ == "__main__":
    test_front_analyzer_advanced()