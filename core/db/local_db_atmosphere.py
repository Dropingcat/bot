# -*- coding: utf-8 -*-
"""
Локальная база данных для кэширования атмосферных данных.

Используется для:
- Хранения фаз Луны
- Кэширования прозрачности неба
- Данных о световом загрязнении
- Астрономических прогнозов

Таблицы:
- atmosphere_cache: кэш атмосферных данных
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from config.db_config import ATMOSPHERE_CACHE_DB

logger = logging.getLogger("local_db_atmosphere")

# === SQL ЗАПРОСЫ ===
CREATE_TABLES_SQL = """
-- Кэш атмосферных данных
CREATE TABLE IF NOT EXISTS atmosphere_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    timestamp DATETIME NOT NULL,
    data_type TEXT NOT NULL,  -- 'moon_phase', 'sky_transparency', 'light_pollution'
    date DATE NOT NULL,       -- дата (для лунных фаз)
    data_json TEXT NOT NULL,  -- сериализованные данные
    source TEXT DEFAULT 'calculation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_atmosphere_coords_type_date 
ON atmosphere_cache (lat, lon, data_type, date, expires_at);
"""

# === УТИЛИТЫ ===
def get_db_connection():
    conn = sqlite3.connect(ATMOSPHERE_CACHE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db_path = Path(ATMOSPHERE_CACHE_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("Локальная БД атмосферы инициализирована: %s", ATMOSPHERE_CACHE_DB)
    except Exception as e:
        logger.error("Ошибка инициализации локальной БД атмосферы: %s", e)
        raise
    finally:
        conn.close()


# === КЭШ АТМОСФЕРНЫХ ДАННЫХ ===
def cache_atmosphere_data(
    lat: float,
    lon: float,
    data_type: str,
    date: datetime,
    atmosphere_ Dict,  # ← ПРАВИЛЬНОЕ ИМЯ АРГУМЕНТА
    source: str = "calculation",
    ttl_hours: int = 168  # 1 неделя
) -> bool:
    """Кэширует атмосферные данные (лунная фаза, прозрачность и т.д.)."""
    conn = get_db_connection()
    try:
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        data_json = json.dumps(atmosphere_data, ensure_ascii=False)  # ← ИСПОЛЬЗУЕМ ПРАВИЛЬНОЕ ИМЯ

        conn.execute(
            """
            INSERT INTO atmosphere_cache
            (lat, lon, timestamp, data_type, date, data_json, source, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (lat, lon, datetime.utcnow(), data_type, date.date(), data_json, source, expires_at)
        )
        conn.commit()
        logger.debug("Кэшированы атмосферные данные %s для (%s, %s)", data_type, lat, lon)
        return True
    except Exception as e:
        logger.error("Ошибка кэширования атмосферных данных: %s", e)
        return False
    finally:
        conn.close()


def get_cached_atmosphere_data(
    lat: float,
    lon: float,
    data_type: str,
    date: datetime
) -> Optional[Dict]:
    """Получает кэшированные атмосферные данные."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT data_json
            FROM atmosphere_cache
            WHERE lat = ? AND lon = ? AND data_type = ? AND date = ?
              AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (lat, lon, data_type, date.date(), datetime.utcnow())
        )
        row = cursor.fetchone()
        return json.loads(row["data_json"]) if row else None
    except Exception as e:
        logger.error("Ошибка получения кэша атмосферы: %s", e)
        return None
    finally:
        conn.close()


def cleanup_expired_atmosphere_cache() -> int:
    """Удаляет устаревшие записи из кэша атмосферы."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM atmosphere_cache WHERE expires_at <= ?",
            (datetime.utcnow(),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            logger.info("Удалено %d устаревших записей из кэша атмосферы", deleted_count)
        return deleted_count
    except Exception as e:
        logger.error("Ошибка очистки кэша атмосферы: %s", e)
        return 0
    finally:
        conn.close()