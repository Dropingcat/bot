# -*- coding: utf-8 -*-
"""
Тест: api_client — запрос с диапазоном дат (days=7)
"""

from core.utils.api_client import APIClient

def test_date_range():
    print("🧪 Тест: api_client — диапазон дат (days=7)")
    client = APIClient()

    # Запрос на 7 дней
    data = client.get_weather_data(55.75, 37.62, days=7)

    if data and "hourly" in data and len(data["hourly"].get("time", [])) > 0:
        print("✅ Прогноз на 7 дней получен")
        
        # === 1. Проверяем структуру ===
        hourly = data.get("hourly", {})
        daily = data.get("daily", {})
        
        print(f"📊 Hourly keys: {list(hourly.keys())}")
        print(f"📊 Daily keys: {list(daily.keys())}")

        # === 2. Проверяем количество точек ===
        time_hourly = hourly.get("time", [])
        time_daily = daily.get("time", [])

        print(f"📅 Количество почасовых точек: {len(time_hourly)}")
        print(f"📅 Количество суточных точек: {len(time_daily)}")

        # === 3. Примеры данных ===
        temp_2m = hourly.get("temperature_2m", [])
        rh_2m = hourly.get("relative_humidity_2m", [])
        pres = hourly.get("pressure_msl", [])
        cloud = hourly.get("cloud_cover", [])
        wind_sp = hourly.get("wind_speed_10m", [])
        wind_dir = hourly.get("wind_direction_10m", [])

        print(f"🌡️  Температура 2м (первые 5): {temp_2m[:5]}")
        print(f"💧 Влажность 2м (первые 5): {rh_2m[:5]}")
        print(f"🔽 Давление (первые 5): {pres[:5]}")
        print(f"☁️  Облачность (первые 5): {cloud[:5]}")
        print(f"💨 Скорость ветра (первые 5): {wind_sp[:5]}")
        print(f"🧭 Направление ветра (первые 5): {wind_dir[:5]}")

        # === 4. Проверяем, что есть данные ===
        if len(temp_2m) > 0:
            print("✅ Температура: данные есть")
        else:
            print("❌ Температура: данных нет")

        if len(rh_2m) > 0:
            print("✅ Влажность: данные есть")
        else:
            print("❌ Влажность: данных нет")

        if len(pres) > 0:
            print("✅ Давление: данные есть")
        else:
            print("❌ Давление: данных нет")

        # === 5. Суточные данные ===
        daily_temp_max = daily.get("temperature_2m_max", [])
        daily_temp_min = daily.get("temperature_2m_min", [])
        daily_precip = daily.get("precipitation_sum", [])

        print(f"🌞 Суточная T_max (7 дней): {daily_temp_max}")
        print(f"🌙 Суточная T_min (7 дней): {daily_temp_min}")
        print(f"🌧️  Суточные осадки (7 дней): {daily_precip}")

        # === 6. Проверка длины ===
        expected_hourly_points = 7 * 24  # 7 дней × 24 часа
        if len(time_hourly) == expected_hourly_points:
            print(f"✅ Проверка: {expected_hourly_points} почасовых точек — корректно")
        else:
            print(f"❌ Проверка: ожидалось {expected_hourly_points}, получено {len(time_hourly)}")

        if len(time_daily) == 7:
            print("✅ Проверка: 7 суточных точек — корректно")
        else:
            print(f"❌ Проверка: ожидалось 7, получено {len(time_daily)}")

    else:
        print("❌ Ошибка: данные не получены")

    print("\n✅ Тест диапазона дат завершён")


if __name__ == "__main__":
    test_date_range()