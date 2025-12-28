"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Центральная база данных: пользователи и локации.
Использует SQLite в синхронном режиме.
"""

import sqlite3
import threading
from pathlib import Path
from typing import List, Optional, Tuple

from config.db_config import CENTRAL_DB_PATH


class CentralDB:
    """
    Singleton-совместимый класс для работы с центральной БД.
    Потокобезопасен за счёт локального подключения в каждом методе.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or CENTRAL_DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Создаёт новое подключение к БД (потокобезопасно)."""
        # check_same_thread=False безопасно, т.к. соединение локальное для метода
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row  # доступ по имени колонки
        return conn

    def _init_db(self):
        """Инициализирует таблицы при первом запуске."""
        with self._get_connection() as conn:
            # Таблица пользователей
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица локаций
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    location_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    is_default BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                    UNIQUE(user_id, location_id)
                )
            """)

            # Индекс для быстрого поиска локации по умолчанию
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_default_location
                ON user_locations (user_id, is_default)
                WHERE is_default = 1
            """)

    def create_or_get_user(self, telegram_id: int) -> int:
        """Создаёт пользователя, если не существует. Возвращает telegram_id."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
                (telegram_id,)
            )
            return telegram_id

    def add_location(
        self,
        user_id: int,
        location_id: str,
        display_name: str,
        lat: float,
        lon: float,
        is_default: bool = False  # ← оставим для обратной совместимости
    ) -> None:
        with self._get_connection() as conn:
            # Проверяем, есть ли уже локации
            existing_count = conn.execute(
                "SELECT COUNT(*) FROM user_locations WHERE user_id = ?",
                (user_id,)
            ).fetchone()[0]

            # Если это первая локация — она ДОЛЖНА быть текущей
            if existing_count == 0:
                is_default = True

            if is_default:
                conn.execute(
                    "UPDATE user_locations SET is_default = FALSE WHERE user_id = ?",
                    (user_id,)
                )

            conn.execute(
                """
                INSERT INTO user_locations 
                (user_id, location_id, display_name, lat, lon, is_default)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, location_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    lat = excluded.lat,
                    lon = excluded.lon,
                    is_default = excluded.is_default
                """,
                (user_id, location_id, display_name, lat, lon, is_default)
            )


    def get_default_location(self, user_id: int) -> Optional[dict]:
        """
        Возвращает локацию по умолчанию в виде словаря.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT location_id, display_name, lat, lon
                FROM user_locations
                WHERE user_id = ? AND is_default = TRUE
                """,
                (user_id,)
            ).fetchone()

            return dict(row) if row else None

    def get_user_locations(self, user_id: int) -> List[dict]:
        """Возвращает все локации пользователя."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, location_id, display_name, lat, lon, is_default
                FROM user_locations
                WHERE user_id = ?
                ORDER BY is_default DESC, created_at ASC
                """,
                (user_id,)
            ).fetchall()

            return [dict(row) for row in rows]

    def set_default_location(self, user_id: int, location_id: str) -> bool:
        with self._get_connection() as conn:
            # Проверяем, существует ли локация
            exists = conn.execute(
                "SELECT 1 FROM user_locations WHERE user_id = ? AND location_id = ?",
                (user_id, location_id)
            ).fetchone()

            if not exists:
                return False

            # Снимаем флаг со всех
            conn.execute(
                "UPDATE user_locations SET is_default = FALSE WHERE user_id = ?",
                (user_id,)
            )
            # Устанавливаем новый флаг
            conn.execute(
                "UPDATE user_locations SET is_default = TRUE WHERE user_id = ? AND location_id = ?",
                (user_id, location_id)
            )
            return True
    def remove_location(self, user_id: int, location_id: str) -> bool:
        with self._get_connection() as conn:
            # Проверяем, была ли это локация по умолчанию
            was_default = conn.execute(
                "SELECT is_default FROM user_locations WHERE user_id = ? AND location_id = ?",
                (user_id, location_id)
            ).fetchone()

            # Удаляем
            conn.execute(
                "DELETE FROM user_locations WHERE user_id = ? AND location_id = ?",
                (user_id, location_id)
            )

            # Если удалили локацию по умолчанию — назначаем первую
            if was_default and was_default[0]:
                conn.execute(
                    """
                    UPDATE user_locations
                    SET is_default = TRUE
                    WHERE user_id = ? AND id = (
                        SELECT id FROM user_locations WHERE user_id = ? LIMIT 1
                    )
                    """,
                    (user_id, user_id)
                )
            return True