# -*- coding: utf-8 -*-
"""
Тесты для core/db/local_db_atmosphere.py
"""
import tempfile
import os
from datetime import datetime
from pathlib import Path

from config import db_config
original_path = db_config.ATMOSPHERE_CACHE_DB

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_db_path = tmp.name

db_config.ATMOSPHERE_CACHE_DB = Path(temp_db_path)

from core.db.local_db_atmosphere import init_db, cache_atmosphere_data, get_cached_atmosphere_data

def test_local_db_atmosphere():
    init_db()
    
    lat, lon = 55.75, 37.62
    date = datetime(2025, 1, 1)
    
    # Тест кэширования лунной фазы
    moon_data = {"phase": "full_moon", "illumination": 0.99, "distance_km": 363104}
    success = cache_atmosphere_data(lat, lon, "moon_phase", date, moon_data)
    assert success == True
    
    cached = get_cached_atmosphere_data(lat, lon, "moon_phase", date)
    assert cached == moon_data
    
    # Тест кэширования прозрачности неба
    transparency_data = {"value": 0.85, "visibility_km": 25.0, "humidity_effect": 0.1}
    success = cache_atmosphere_data(lat, lon, "sky_transparency", date, transparency_data)
    assert success == True
    
    cached = get_cached_atmosphere_data(lat, lon, "sky_transparency", date)
    assert cached == transparency_data
    
    print("✅ test_local_db_atmosphere passed")
    
    # Восстановление
    db_config.ATMOSPHERE_CACHE_DB = original_path
    os.unlink(temp_db_path)


if __name__ == "__main__":
    test_local_db_atmosphere()