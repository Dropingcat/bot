"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Центральная база данных (ЦБД) проекта.

Хранит:
- пользователей (user_id)
- локации пользователей (lat, lon, name, is_default)
- профили (для метео-моделей)
- растения (для агропрогноза)

Использует SQLite через встроенный модуль sqlite3.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from config.db_config import CENTRAL_DB_PATH

logger = logging.getLogger("central_db")

# === SQL ЗАПРОСЫ ===
CREATE_TABLES_SQL = """
-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица локаций пользователей
CREATE TABLE IF NOT EXISTS user_locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE(user_id, lat, lon)
);

-- Индекс для быстрого поиска локаций по user_id
CREATE INDEX IF NOT EXISTS idx_user_locations_user_id ON user_locations (user_id);

-- Индекс для поиска локации по умолчанию
CREATE INDEX IF NOT EXISTS idx_user_locations_default ON user_locations (user_id, is_default) WHERE is_default = 1;

-- Таблица профилей пользователей (для метео-моделей)
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY,
    age INTEGER,
    health_conditions TEXT,  -- JSON строка
    weather_sensitivity REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Таблица растений пользователей (для агропрогноза)
CREATE TABLE IF NOT EXISTS user_plants (
    plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    species TEXT,  -- вид растения
    planted_at DATE,
    location_id INTEGER,  -- привязка к локации
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES user_locations (location_id) ON DELETE SET NULL
);
"""

# === УТИЛИТЫ ===
def get_db_connection():
    """Возвращает соединение с базой данных."""
    conn = sqlite3.connect(CENTRAL_DB_PATH)
    conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
    return conn


def init_db():
    """Инициализирует базу данных: создаёт таблицы, если не существуют."""
    db_path = Path(CENTRAL_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)  # Создаём папку, если нет

    conn = get_db_connection()
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("Центральная БД инициализирована: %s", CENTRAL_DB_PATH)
    except Exception as e:
        logger.error("Ошибка инициализации БД: %s", e)
        raise
    finally:
        conn.close()


# === CRUD: ПОЛЬЗОВАТЕЛИ ===
def add_user(user_id: int) -> bool:
    """
    Добавляет пользователя в базу.

    Args:
        user_id (int): Telegram user_id

    Returns:
        bool: True, если пользователь добавлен (или уже существовал)
    """
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        logger.debug("Добавлен пользователь: %s", user_id)
        return True
    except Exception as e:
        logger.error("Ошибка добавления пользователя %s: %s", user_id, e)
        return False
    finally:
        conn.close()


def user_exists(user_id: int) -> bool:
    """Проверяет, существует ли пользователь."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


# === CRUD: ЛОКАЦИИ ===
def get_user_locations(user_id: int) -> List[Dict]:
    """
    Возвращает все локации пользователя.

    Args:
        user_id (int): ID пользователя

    Returns:
        List[Dict]: Список словарей с ключами: location_id, name, lat, lon, is_default
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT location_id, name, lat, lon, is_default
            FROM user_locations
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_user_location(user_id: int, name: str, lat: float, lon: float, is_default: bool = False) -> Optional[int]:
    """
    Добавляет новую локацию пользователю.

    Args:
        user_id (int): ID пользователя
        name (str): Название локации (например, "Дом", "Дача")
        lat (float): Широта
        lon (float): Долгота
        is_default (bool): Сделать ли локацию по умолчанию

    Returns:
        Optional[int]: ID новой локации или None при ошибке
    """
    conn = get_db_connection()
    try:
        # Если устанавливаем как default, сбрасываем флаг у других
        if is_default:
            conn.execute(
                "UPDATE user_locations SET is_default = 0 WHERE user_id = ?",
                (user_id,)
            )

        cursor = conn.execute(
            """
            INSERT INTO user_locations (user_id, name, lat, lon, is_default)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, lat, lon, is_default)
        )
        conn.commit()
        location_id = cursor.lastrowid

        logger.debug("Добавлена локация для %s: %s (%s, %s)", user_id, name, lat, lon)
        return location_id
    except sqlite3.IntegrityError:
        logger.warning("Локация (%s, %s) уже существует для пользователя %s", lat, lon, user_id)
        return None
    except Exception as e:
        logger.error("Ошибка добавления локации: %s", e)
        return None
    finally:
        conn.close()


def remove_user_location(user_id: int, location_id: int) -> bool:
    """
    Удаляет локацию пользователя.

    Args:
        user_id (int): ID пользователя
        location_id (int): ID локации

    Returns:
        bool: True, если удалено
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM user_locations WHERE user_id = ? AND location_id = ?",
            (user_id, location_id)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug("Удалена локация %s для пользователя %s", location_id, user_id)
        return deleted
    except Exception as e:
        logger.error("Ошибка удаления локации: %s", e)
        return False
    finally:
        conn.close()


def set_default_location(user_id: int, location_id: int) -> bool:
    """
    Устанавливает локацию по умолчанию для пользователя.

    Args:
        user_id (int): ID пользователя
        location_id (int): ID локации

    Returns:
        bool: True, если успешно
    """
    conn = get_db_connection()
    try:
        # Сбрасываем флаг у всех
        conn.execute("UPDATE user_locations SET is_default = 0 WHERE user_id = ?", (user_id,))
        # Устанавливаем для выбранной
        cursor = conn.execute(
            "UPDATE user_locations SET is_default = 1 WHERE user_id = ? AND location_id = ?",
            (user_id, location_id)
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.debug("Установлена локация по умолчанию %s для пользователя %s", location_id, user_id)
        return success
    except Exception as e:
        logger.error("Ошибка установки локации по умолчанию: %s", e)
        return False
    finally:
        conn.close()


def get_default_location(user_id: int) -> Optional[Dict]:
    """
    Возвращает локацию по умолчанию для пользователя.

    Args:
        user_id (int): ID пользователя

    Returns:
        Optional[Dict]: Словарь с локацией или None
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT location_id, name, lat, lon
            FROM user_locations
            WHERE user_id = ? AND is_default = 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# === CRUD: ПРОФИЛИ (опционально) ===
def get_or_create_user_profile(user_id: int) -> Dict:
    """
    Возвращает профиль пользователя, создавая его при отсутствии.

    Args:
        user_id (int): ID пользователя

    Returns:
        Dict: Профиль пользователя
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)
            """,
            (user_id,)
        )
        conn.commit()

        cursor = conn.execute(
            """
            SELECT age, health_conditions, weather_sensitivity
            FROM user_profiles
            WHERE user_id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else {"age": None, "health_conditions": None, "weather_sensitivity": 0.0}
    finally:
        conn.close()


def update_user_profile(user_id: int, **kwargs) -> bool:
    """
    Обновляет поля профиля пользователя.

    Args:
        user_id (int): ID пользователя
        **kwargs: Поля для обновления (age, health_conditions, weather_sensitivity)

    Returns:
        bool: True, если успешно
    """
    allowed_fields = {"age", "health_conditions", "weather_sensitivity"}
    update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

    if not update_fields:
        return True  # Нечего обновлять

    set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
    values = list(update_fields.values()) + [user_id]

    conn = get_db_connection()
    try:
        conn.execute(
            f"UPDATE user_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            values
        )
        conn.commit()
        logger.debug("Обновлён профиль пользователя %s: %s", user_id, update_fields)
        return True
    except Exception as e:
        logger.error("Ошибка обновления профиля %s: %s", user_id, e)
        return False
    finally:
        conn.close()


# === CRUD: РАСТЕНИЯ (опционально) ===
def add_user_plant(user_id: int, name: str, species: str = None, location_id: int = None) -> Optional[int]:
    """
    Добавляет растение пользователю.

    Args:
        user_id (int): ID пользователя
        name (str): Название растения
        species (str): Вид (опционально)
        location_id (int): Привязка к локации (опционально)

    Returns:
        Optional[int]: ID растения или None
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO user_plants (user_id, name, species, location_id)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, species, location_id)
        )
        conn.commit()
        plant_id = cursor.lastrowid
        logger.debug("Добавлено растение для %s: %s", user_id, name)
        return plant_id
    except Exception as e:
        logger.error("Ошибка добавления растения: %s", e)
        return None
    finally:
        conn.close()