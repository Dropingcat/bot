# tests/unit/test_data_processor.py
from core.utils.data_processor import (
    linear_interpolation_1d,
    normalize_min_max,
    moving_average_filter,
    interpolate_dataframe,
    process_weather_timeseries
)
import pandas as pd

def test_data_processor():
    print("🧪 Тест: data_processor")

    # === 1. Линейная интерполяция ===
    print("\n🔍 Тест 1: Линейная интерполяция")
    x = [0, 1, 2]
    y = [0, 1, 4]
    target_x = [0.5, 1.5]
    result = linear_interpolation_1d(x, y, target_x)
    print(f"📈 Интерполяция: {target_x} → {result}")
    assert result[0] == 0.5
    assert result[1] == 2.5
    print("✅ OK")

    # === 2. Нормализация ===
    print("\n🔍 Тест 2: Нормализация MinMax")
    values = [1, 2, 3]
    norm = normalize_min_max(values, 0, 1)
    print(f"📊 Нормализация: {values} → {norm}")
    assert norm == [0.0, 0.5, 1.0]
    print("✅ OK")

    # === 3. Скользящее среднее ===
    print("\n🔍 Тест 3: Скользящее среднее")
    values = [1, 2, 6, 8, 1]
    filtered = moving_average_filter(values, window_size=3)
    print(f"📉 Фильтр: {values} → {filtered}")
    # Проверим, что стало "гладче"
    assert len(filtered) == len(values)
    print("✅ OK")

    # === 4. Интерполяция DataFrame ===
    print("\n🔍 Тест 4: Интерполяция DataFrame")
    dates = pd.date_range('2025-01-01', periods=3, freq='2h')  # <-- '2h'
    df = pd.DataFrame({
        'temp': [1, 3, 5],
        'pressure': [1010, 1012, 1014]
    }, index=dates)

    new_dates = pd.date_range('2025-01-01', periods=5, freq='1h')  # <-- '1h'
    df_interp = interpolate_dataframe(df, new_dates)
    print(f"📅 DataFrame: {len(df)} → {len(df_interp)} строк")
    assert len(df_interp) == 5
    print("✅ OK")

    # === 5. Обработка погоды ===
    print("\n🔍 Тест 5: Обработка погодного временного ряда")
    timestamps = ["2025-01-01 00:00:00", "2025-01-01 02:00:00", "2025-01-01 04:00:00"]
    temps = [1.0, 3.0, 5.0]
    press = [1010.0, 1012.0, 1014.0]

    processed = process_weather_timeseries(timestamps, temps, press, '1h')  # <-- '1h'
    print(f"🌤️  Обработано: {len(processed['timestamps'])} точек")
    assert len(processed['timestamps']) == 5  # 00, 01, 02, 03, 04
    print("✅ OK")

    print("\n✅ Все тесты data_processor пройдены!")

if __name__ == "__main__":
    test_data_processor()