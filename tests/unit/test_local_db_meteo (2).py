# -*- coding: utf-8 -*-
"""
Тест: local_db_meteo.py — все функции
"""

import tempfile
import os
from pathlib import Path
import random
from datetime import datetime, timedelta

# Подменяем БД для теста
from config import db_config
original_meteo_db = db_config.METEO_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_meteo_db = tmp.name

db_config.METEO_DB = Path(temp_meteo_db)

from core.db.local_db_meteo import (
    init_db,
    save_user_profile,
    get_user_profile,
    save_user_health_log,
    get_user_health_log,
    get_user_health_stats,
    save_front_analysis,
    get_recent_front_analysis,
    save_health_impact_prediction,
    get_user_health_predictions
)

def test_local_db_meteo():
    print("🧪 ТЕСТ: local_db_meteo.py — все функции")
    print("="*60)

    results = []

    # === 1. ИНИЦИАЛИЗАЦИЯ БД ===
    print("\n🔍 Тест 1: Инициализация БД")
    try:
        init_db()
        print("✅ БД инициализирована")
        results.append(("Инициализация", True, "OK"))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Инициализация", False, str(e)))

    # === 2. СОЗДАНИЕ ПРОФИЛЯ ===
    print("\n🔍 Тест 2: Создание профиля пользователя")
    user_id = 12345
    profile_data = {
        "health_category": "hypertensive",
        "age": 45,
        "weight": 78.5,
        "height": 175,
        "baseline_systolic": 130.0,
        "baseline_diastolic": 85.0,
        "baseline_heart_rate": 72,
        "baseline_spo2": 98.0,
        "baseline_symptoms": {"migraine": 2, "drowsiness": 1}
    }
    try:
        save_user_profile(user_id, profile_data)
        retrieved = get_user_profile(user_id)
        if retrieved and retrieved["health_category"] == "hypertensive":
            print("✅ Профиль сохранён и получен")
            results.append(("Профиль", True, "OK"))
        else:
            print("❌ Профиль не совпадает")
            results.append(("Профиль", False, "Data mismatch"))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Профиль", False, str(e)))

    # === 3. ЗАПИСЬ ЖУРНАЛА САМОЧУВСТВИЯ (20 точек) ===
    print("\n🔍 Тест 3: Запись 20 точек самочувствия")
    try:
        base_time = datetime.now() - timedelta(days=1)
        for i in range(20):
            timestamp = (base_time + timedelta(minutes=i * 30)).isoformat()
            save_user_health_log(
                user_id=user_id,
                timestamp=timestamp,
                systolic=120 + random.randint(-20, 20),
                diastolic=80 + random.randint(-10, 10),
                heart_rate=70 + random.randint(-10, 10),
                spo2=97 + random.random(),
                migraine=random.randint(0, 10),
                drowsiness=random.randint(0, 10),
                anxiety=random.randint(0, 10),
                depression=random.randint(0, 10),
                excitement=random.randint(0, 10),
                malaise=random.randint(0, 10),
                comment=f"Тест {i}"
            )
        print("✅ 20 точек записано")
        results.append(("Запись журнала", True, "OK"))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Запись журнала", False, str(e)))

    # === 4. ПОЛУЧЕНИЕ ЖУРНАЛА ===
    print("\n🔍 Тест 4: Получение журнала за период")
    try:
        start = (datetime.now() - timedelta(hours=1)).isoformat()
        end = datetime.now().isoformat()
        logs = get_user_health_log(user_id, start, end)
        if len(logs) >= 2:  # хотя бы 2 точки
            print(f"✅ Получено {len(logs)} записей")
            print(f"   Пример: {logs[0]['systolic']}, {logs[0]['heart_rate']}")
            results.append(("Получение журнала", True, f"OK: {len(logs)} записей"))
        else:
            print(f"❌ Мало записей: {len(logs)}")
            results.append(("Получение журнала", False, f"Too few records: {len(logs)}"))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Получение журнала", False, str(e)))

    # === 5. СТАТИСТИКА ===
    print("\n🔍 Тест 5: Получение статистики")
    try:
        stats = get_user_health_stats(user_id)
        if stats.get("avg_systolic"):
            print(f"✅ Среднее АД: {stats['avg_systolic']:.1f}")
            results.append(("Статистика", True, "OK"))
        else:
            print("❌ Статистика пуста")
            results.append(("Статистика", False, "No stats"))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Статистика", False, str(e)))

    # === 6. АНАЛИЗ ФРОНТОВ ===
    print("\n🔍 Тест 6: Анализ фронтов")
    try:
        analysis_data = {
            "pressure_gradient": 1.2,
            "temperature_gradient": 0.8,
            "wind_oscillation": 3.5,
            "baric_anomaly": -2.1,
            "front_distance_km": 50.0,
            "front_direction": "NE",
            "front_type": "cold"
        }
        save_front_analysis(55.75, 37.62, datetime.now().isoformat(), analysis_data)
        front_logs = get_recent_front_analysis(55.75, 37.62, hours_back=1)
        if len(front_logs) > 0:
            print(f"✅ Фронт сохранён: {front_logs[0]['front_type']}")
            results.append(("Фронты", True, "OK"))
        else:
            print("❌ Фронт не найден")
            results.append(("Фронты", False, "No front data"))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Фронты", False, str(e)))

    # === 7. ПРОГНОЗ ВЛИЯНИЯ ===
    print("\n🔍 Тест 7: Прогноз влияния на здоровье")
    try:
        prediction_data = {
            "risk_level": "medium",
            "risk_category": "hypertensive",
            "risk_comment": "Ожидается рост АД из-за приближения фронта",
            "risk_score": 0.6,
            "forecast_json": {"ad_change": "+10", "hr_change": "+5"}
        }
        save_health_impact_prediction(user_id, datetime.now().isoformat(), prediction_data)
        predictions = get_user_health_predictions(user_id)
        if len(predictions) > 0:
            print(f"✅ Прогноз сохранён: {predictions[0]['risk_comment']}")
            results.append(("Прогноз", True, "OK"))
        else:
            print("❌ Прогноз не найден")
            results.append(("Прогноз", False, "No prediction"))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append(("Прогноз", False, str(e)))

    # === 8. ТЕСТ НА ПЕРЕПОЛНЕНИЕ (слишком длинный комментарий) ===
    print("\n🔍 Тест 8: Тест на отказ при длинном комментарии")
    try:
        long_comment = "A" * 10000  # очень длинный текст
        save_user_health_log(
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            systolic=120, diastolic=80, heart_rate=70, spo2=98.0,
            comment=long_comment
        )
        print("✅ Длинный комментарий записан")
        results.append(("Переполнение", True, "OK"))
    except Exception as e:
        print(f"✅ Длинный комментарий вызвал ошибку (ожидаемо): {e}")
        results.append(("Переполнение", True, f"Expected error: {e}"))

    # === 9. ТЕСТ НА ОТКАЗ (неправильный user_id) ===
    print("\n🔍 Тест 9: Тест на отказ при неправильном user_id")
    try:
        retrieved = get_user_profile(-1)  # несуществующий
        if retrieved is None:
            print("✅ Пустой ответ для несуществующего user_id")
            results.append(("Отказ", True, "OK"))
        else:
            print("❌ Непустой ответ для несуществующего user_id")
            results.append(("Отказ", False, "Got data for invalid user_id"))
    except Exception as e:
        print(f"✅ Ошибка для неверного user_id (ожидаемо): {e}")
        results.append(("Отказ", True, f"Expected error: {e}"))

    # === ОТЧЁТ ===
    print("\n" + "="*60)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТА local_db_meteo")
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

    # === ОЧИСТКА ===
    db_config.METEO_DB = original_meteo_db
    if os.path.exists(temp_meteo_db):
        os.unlink(temp_meteo_db)
    print(f"🧹 Временная БД удалена: {temp_meteo_db}")


if __name__ == "__main__":
    test_local_db_meteo()