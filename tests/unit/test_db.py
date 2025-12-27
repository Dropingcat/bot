# -*- coding: utf-8 -*-
"""
Тест для core/db/central_db.py
Сценарий:
- Создаёт пользователя
- Добавляет 2 локации
- Устанавливает одну по умолчанию
- Читает локации
- Удаляет одну
- Проверяет корректность
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

def test_db():
    print("🧪 Запуск теста central_db...")
    
    # 1. Инициализация
    init_db()
    print("✅ init_db() — OK")
    
    user_id = 123456
    
    # 2. Добавление пользователя
    success = add_user(user_id)
    assert success == True, "❌ add_user не вернул True"
    print("✅ add_user(123456) — OK")
    
    # 3. Добавление локаций
    loc1_id = add_user_location(user_id, "Дом", 55.75, 37.62)
    loc2_id = add_user_location(user_id, "Дача", 56.0, 38.0)
    
    assert loc1_id is not None, "❌ add_user_location не вернул ID"
    assert loc2_id is not None, "❌ add_user_location не вернул ID"
    assert loc1_id != loc2_id, "❌ ID локаций совпадают"
    
    print(f"✅ add_user_location('Дом', 55.75, 37.62) → ID {loc1_id}")
    print(f"✅ add_user_location('Дача', 56.0, 38.0) → ID {loc2_id}")
    
    # 4. Проверка получения локаций
    locations = get_user_locations(user_id)
    assert len(locations) == 2, f"❌ get_user_locations вернул {len(locations)}, ожидалось 2"
    
    names = {loc["name"] for loc in locations}
    assert "Дом" in names, "❌ Локация 'Дом' не найдена"
    assert "Дача" in names, "❌ Локация 'Дача' не найдена"
    
    print(f"✅ get_user_locations(123456) → {len(locations)} локаций: {names}")
    
    # 5. Установка локации по умолчанию
    success = set_default_location(user_id, loc1_id)
    assert success == True, "❌ set_default_location не вернул True"
    
    default_loc = get_default_location(user_id)
    assert default_loc is not None, "❌ get_default_location вернул None"
    assert default_loc["location_id"] == loc1_id, f"❌ get_default_location вернул ID {default_loc['location_id']}, ожидалось {loc1_id}"
    assert default_loc["name"] == "Дом", f"❌ get_default_location вернул имя '{default_loc['name']}', ожидалось 'Дом'"
    
    print(f"✅ set_default_location(123456, {loc1_id}) — OK")
    print(f"✅ get_default_location(123456) → {default_loc['name']} (ID: {default_loc['location_id']})")
    
    # 6. Удаление одной локации
    success = remove_user_location(user_id, loc2_id)
    assert success == True, "❌ remove_user_location не вернул True"
    
    locations_after = get_user_locations(user_id)
    assert len(locations_after) == 1, f"❌ get_user_locations после удаления вернул {len(locations_after)}, ожидалось 1"
    assert locations_after[0]["name"] == "Дом", f"❌ Оставшаяся локация — '{locations_after[0]['name']}', ожидалось 'Дом'"
    
    print(f"✅ remove_user_location(123456, {loc2_id}) — OK")
    print(f"✅ get_user_locations(123456) после удаления → {len(locations_after)} локация: {locations_after[0]['name']}")
    
    # 7. Проверка, что локация по умолчанию осталась
    default_after = get_default_location(user_id)
    assert default_after is not None, "❌ get_default_location стал None после удаления другой локации"
    assert default_after["location_id"] == loc1_id, f"❌ get_default_location после удаления сменил ID на {default_after['location_id']}"
    
    print(f"✅ get_default_location(123456) после удаления — всё ещё 'Дом' (ID: {default_after['location_id']})")
    
    print("\n🎉 Все проверки пройдены успешно!")


if __name__ == "__main__":
    test_db()
    
    # Восстанавливаем оригинальный путь
    db_config.CENTRAL_DB_PATH = original_path
    os.unlink(temp_db_path)
    print(f"🧹 Временный файл БД удалён: {temp_db_path}")