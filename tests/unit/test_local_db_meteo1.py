# -*- coding: utf-8 -*-
"""
Тесты для core/db/local_db_meteo.py
"""
import tempfile
import os
from datetime import datetime
from pathlib import Path

from config import db_config
original_path = db_config.METEO_CACHE_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_db_path = tmp.name

db_config.METEO_CACHE_DB = Path(temp_db_path)

from core.db.local_db_meteo import init_db, cache_meteo_impact, get_cached_meteo_impact, cache_front_analysis, get_cached_front_analysis

def test_local_db_meteo():
    init_db()
    
    user_id = 123
    lat, lon = 55.75, 37.62
    forecast_time = datetime(2025, 1, 1, 12, 0, 0)
    
    # Тест кэширования метео-влияния
    impact_data = {"stress_index": 0.7, "bp_change": -5, "health_risk": "medium"}
    success = cache_meteo_impact(user_id, lat, lon, forecast_time, "stress_index", impact_data)
    assert success == True
    
    cached = get_cached_meteo_impact(lat, lon, forecast_time, "stress_index", user_id)
    assert cached == impact_data
    
    # Тест кэширования анализа фронта
    front_data = {
        "front_type": "cold",
        "front_strength": 0.8,
        "front_distance_km": 150.0,
        "gradient": 2.5
    }
    analysis_time = datetime(2025, 1, 1, 10, 0, 0)
    success = cache_front_analysis(lat, lon, analysis_time, front_data)
    assert success == True
    
    cached_front = get_cached_front_analysis(lat, lon, analysis_time)
    assert cached_front == front_data
    
    print("✅ test_local_db_meteo passed")
    
    # Восстановление
    db_config.METEO_CACHE_DB = original_path
    os.unlink(temp_db_path)


if __name__ == "__main__":
    test_local_db_meteo()