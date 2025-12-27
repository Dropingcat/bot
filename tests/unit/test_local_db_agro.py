# -*- coding: utf-8 -*-
"""
Тесты для core/db/local_db_agro.py
"""
import tempfile
import os
from datetime import datetime
from pathlib import Path

from config import db_config
original_path = db_config.AGRO_CACHE_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_db_path = tmp.name

db_config.AGRO_CACHE_DB = Path(temp_db_path)

from core.db.local_db_agro import init_db, cache_agro_forecast, get_cached_agro_forecast, cache_soil_analysis, get_cached_soil_analysis

def test_local_db_agro():
    init_db()
    
    user_id = 456
    lat, lon = 54.0, 38.0
    forecast_date = datetime(2025, 5, 20)
    location_id = 789
    
    # Тест кэширования агропрогноза
    forecast_data = {
        "min_temp": 8.0,
        "max_temp": 18.0,
        "precipitation_mm": 2.5,
        "frost_risk": False,
        "recommendation": "watering_needed"
    }
    success = cache_agro_forecast(user_id, lat, lon, forecast_date, "growth", forecast_data)
    assert success == True
    
    cached = get_cached_agro_forecast(user_id, lat, lon, forecast_date, "growth")
    assert cached == forecast_data
    
    # Тест кэширования анализа почвы
    soil_data = {
        "ph": 6.5,
        "moisture": 0.35,
        "composition": {"sand": 0.4, "clay": 0.3, "silt": 0.3},
        "nutrients": {"nitrogen": "medium", "phosphorus": "low", "potassium": "high"}
    }
    success = cache_soil_analysis(user_id, "composition", soil_data, location_id)
    assert success == True
    
    cached = get_cached_soil_analysis(user_id, "composition", location_id)
    assert cached == soil_data
    
    print("✅ test_local_db_agro passed")
    
    # Восстановление
    db_config.AGRO_CACHE_DB = original_path
    os.unlink(temp_db_path)


if __name__ == "__main__":
    test_local_db_agro()