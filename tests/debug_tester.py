# debug_tester.py
"""
Автотест для отладки сценариев работы с локациями.
Запускается отдельно, имитирует действия пользователя.
"""

import sqlite3
from pathlib import Path
from core.db.central_db import CentralDB
from config.db_config import CENTRAL_DB_PATH

def reset_user_data(user_id: int):
    """Полная очистка данных пользователя для чистого теста."""
    with sqlite3.connect(CENTRAL_DB_PATH) as conn:
        conn.execute("DELETE FROM user_locations WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE telegram_id = ?", (user_id,))

def test_scenario():
    user_id = 123456789  # замените на ваш ID
    reset_user_data(user_id)

    db = CentralDB()
    print("1. Добавление первой локации (геопозиция)...")
    db.create_or_get_user(user_id)
    db.add_location(user_id, "geo:55.7558:37.6176", "Москва", 55.7558, 37.6176, is_default=True)

    print("2. Добавление второй локации (текст)...")
    db.add_location(user_id, "text:abc123", "Питер", 0.0, 0.0, is_default=False)

    print("3. Получение локаций:")
    locations = db.get_user_locations(user_id)
    for loc in locations:
        print(f"   - {loc['display_name']} (по умолчанию: {loc['is_default']})")

    print("4. Назначение 'Питер' текущей...")
    db.set_default_location(user_id, "text:abc123")
    locations = db.get_user_locations(user_id)
    for loc in locations:
        print(f"   - {loc['display_name']} (по умолчанию: {loc['is_default']})")

    print("5. Удаление 'Москва'...")
    db.remove_location(user_id, "geo:55.7558:37.6176")
    locations = db.get_user_locations(user_id)
    for loc in locations:
        print(f"   - {loc['display_name']} (по умолчанию: {loc['is_default']})")

if __name__ == "__main__":
    test_scenario()