# -*- coding: utf-8 -*-
"""
Тесты для core/db/local_db_weather.py
"""
import tempfile
import os
from datetime import datetime
from pathlib import Path

# Подменяем путь к БД
from config import db_config
original_path = db_config.WEATHER_CACHE_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_db_path = tmp.name

db_config.WEATHER_CACHE_DB = Path(temp_db_path)

from core.db.local_db_weather import init_db, cache_weather_data, get_cached_weather

def test_local_db_weather():
    init_db()
    
    user_id = 123
    lat, lon = 55.75, 37.62
    forecast_time = datetime(2025, 1, 1, 12, 0, 0)
    weather_data = {"temperature": 15.5, "pressure": 1013.25, "humidity": 65}
    
    # Кэшируем
    success = cache_weather_data(user_id, lat, lon, forecast_time, weather_data, ttl_hours=1)
    assert success == True
    
    # Читаем
    cached = get_cached_weather(lat, lon, forecast_time, user_id)
    assert cached == weather_data
    
    print("✅ test_local_db_weather passed")
    
    # Восстанавливаем путь
    db_config.WEATHER_CACHE_DB = original_path
    os.unlink(temp_db_path)


if __name__ == "__main__":
    test_local_db_weather()