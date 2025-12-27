"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Локальная база данных для кэширования погодных данных.

Используется для:
- Хранения прогнозов (часовые/ежедневные)
- Кэширования API-ответов от Open-Meteo и др.
- Ускорения повторных запросов
- Снижения нагрузки на API

Таблицы:
- weather_cache: кэш погоды по координатам и времени
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
from config.db_config import WEATHER_CACHE_DB

logger = logging.getLogger("local_db_weather")

# === SQL ЗАПРОСЫ ===
CREATE_TABLES_SQL = """
-- Кэш погоды
CREATE TABLE IF NOT EXISTS weather_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    forecast_datetime DATETIME NOT NULL,  -- <-- Это поле используется
    data_json TEXT NOT NULL,
    source TEXT DEFAULT 'open_meteo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Индекс для быстрого поиска по координатам и времени
CREATE INDEX IF NOT EXISTS idx_weather_cache_coords_time 
ON weather_cache (lat, lon, forecast_datetime, expires_at);

-- Индекс для очистки устаревших записей
CREATE INDEX IF NOT EXISTS idx_weather_cache_expires 
ON weather_cache (expires_at);
"""

# === УТИЛИТЫ ===
def get_db_connection():
    """Возвращает соединение с локальной БД погоды."""
    conn = sqlite3.connect(WEATHER_CACHE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализирует локальную БД погоды."""
    db_path = Path(WEATHER_CACHE_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("Локальная БД погоды инициализирована: %s", WEATHER_CACHE_DB)
    except Exception as e:
        logger.error("Ошибка инициализации локальной БД погоды: %s", e)
        raise
    finally:
        conn.close()


# === КЭШИРОВАНИЕ ===
# В cache_weather_data:
def cache_weather_data(
    user_id: Optional[int],
    lat: float,
    lon: float,
    data: dict,
    source: str = "open_meteo",
    forecast_datetime: Optional[datetime] = None,  # ✅ Новый параметр
    ttl_hours: int = 24
):
    """
    Кэширует погодные данные.
    """
    conn = get_db_connection()
    try:
        from config.bot_config import CACHE_TTL_HOURS
        expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)

        # === ИСПРАВЛЕНО: если forecast_datetime нет — используем now() ===
        if forecast_datetime is None:
            forecast_datetime = datetime.now()

        conn.execute(
            """
            INSERT OR REPLACE INTO weather_cache
            (user_id, lat, lon, forecast_datetime, data_json, source, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, lat, lon, forecast_datetime.isoformat(), json.dumps(data, ensure_ascii=False, default=str), source, expires_at)
        )
        conn.commit()
        logger.info(f"💾 Погода закэширована для ({lat}, {lon}) через {source}")
    except Exception as e:
        logger.error(f"❌ Ошибка кэширования погоды: {e}")
    finally:
        conn.close()

def get_cached_weather(lat: float, lon: float, forecast_datetime: datetime, source: str = "open_meteo") -> Optional[Dict]:
    """
    Получает кэшированные погодные данные.
   
    Args:
        lat (float): Широта
        lon (float): Долгота
        forecast_datetime (datetime): Дата/время прогноза
        user_id (int, optional): ID пользователя (если нужно учитывать)
        source (str): Источник данных

    Returns:
        Optional[Dict]: Словарь с данными или None, если нет или устарело
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT data_json
            FROM weather_cache
            WHERE lat = ? AND lon = ? AND source = ? AND forecast_datetime = ?
              AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (lat, lon, source, forecast_datetime, datetime.utcnow())
        )
        row = cursor.fetchone()
        return json.loads(row["data_json"]) if row else None
    except Exception as e:
        logger.error(f"❌ Ошибка получения кэша погоды: {e}")
        return None
    finally:
        conn.close()


def cleanup_expired_weather_cache() -> int:
    """
    Удаляет устаревшие записи из кэша.

    Returns:
        int: Количество удалённых записей
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM weather_cache WHERE expires_at <= ?",
            (datetime.utcnow(),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            logger.info("Удалено %d устаревших записей из кэша погоды", deleted_count)
        return deleted_count
    except Exception as e:
        logger.error("Ошибка очистки кэша погоды: %s", e)
        return 0
    finally:
        conn.close()


# === УДОБНЫЕ МЕТОДЫ ===
def get_cached_hourly_weather(
    lat: float,
    lon: float,
    start_time: datetime,
    end_time: datetime,
    user_id: Optional[int] = None
) -> List[Dict]:
    """
    Получает кэшированные почасовые данные в диапазоне.

    Args:
        lat (float): Широта
        lon (float): Долгота
        start_time (datetime): Начало периода
        end_time (datetime): Конец периода
        user_id (int, optional): ID пользователя

    Returns:
        List[Dict]: Список словарей с данными на каждый час
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT forecast_datetime, data_json
            FROM weather_cache
            WHERE lat = ? AND lon = ? 
              AND forecast_datetime BETWEEN ? AND ?
              AND expires_at > ?
              AND (user_id = ? OR user_id IS NULL)
            ORDER BY forecast_datetime
            """,
            (lat, lon, start_time, end_time, datetime.utcnow(), user_id)
        )
        rows = cursor.fetchall()
        return [{"datetime": row["forecast_datetime"], **json.loads(row["data_json"])} for row in rows]
    except Exception as e:
        logger.error("Ошибка получения почасового кэша: %s", e)
        return []
    finally:
        conn.close()


def clear_user_weather_cache(user_id: int) -> int:
    """
    Очищает кэш погоды для конкретного пользователя.

    Args:
        user_id (int): ID пользователя

    Returns:
        int: Количество удалённых записей
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM weather_cache WHERE user_id = ?",
            (user_id,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        logger.debug("Очищен кэш погоды для пользователя %s: %d записей", user_id, deleted_count)
        return deleted_count
    except Exception as e:
        logger.error("Ошибка очистки кэша пользователя %s: %s", user_id, e)
        return 0
    finally:
        conn.close()