# -*- coding: utf-8 -*-
"""
Тесты для core/db/central_db.py
"""
import tempfile
import os
from pathlib import Path

# Подменяем путь к БД на временный файл для тестов
from config import db_config
original_path = db_config.CENTRAL_DB_PATH

with tempfile.NamedTemporaryFile(delete=False) as tmp:
    temp_db_path = tmp.name

db_config.CENTRAL_DB_PATH = Path(temp_db_path)

from core.db.central_db import init_db, add_user, get_user_locations, add_user_location, remove_user_location, set_default_location, get_default_location

def test_central_db():
    # Инициализация
    init_db()
    
    user_id = 123456
    
    # Добавление пользователя
    assert add_user(user_id) == True
    assert add_user(user_id) == True  # Повторное добавление — ок
    
    # Добавление локаций
    loc1_id = add_user_location(user_id, "Дом", 55.75, 37.62)
    loc2_id = add_user_location(user_id, "Дача", 56.0, 38.0, is_default=True)
    
    assert loc1_id is not None
    assert loc2_id is not None
    assert loc1_id != loc2_id
    
    # Проверка локаций
    locations = get_user_locations(user_id)
    assert len(locations) == 2
    names = {loc["name"] for loc in locations}
    assert "Дом" in names
    assert "Дача" in names
    
    # Проверка default
    default_loc = get_default_location(user_id)
    assert default_loc["name"] == "Дача"
    assert default_loc["lat"] == 56.0
    
    # Смена default
    set_default_location(user_id, loc1_id)
    default_loc = get_default_location(user_id)
    assert default_loc["name"] == "Дом"
    
    # Удаление
    assert remove_user_location(user_id, loc2_id) == True
    locations = get_user_locations(user_id)
    assert len(locations) == 1
    assert locations[0]["name"] == "Дом"
    
    print("✅ test_central_db passed")
    
    # Восстанавливаем оригинальный путь
    db_config.CENTRAL_DB_PATH = original_path
    os.unlink(temp_db_path)


if __name__ == "__main__":
    test_central_db()