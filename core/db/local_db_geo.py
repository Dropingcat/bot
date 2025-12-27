# -*- coding: utf-8 -*-
"""
Локальная БД для кэширования результатов геокодирования.

Таблицы:
- geo_cache: кэш геокодирования (lat, lon → name, display_name, address)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from config.db_config import LOCAL_DB_DIR

GEO_CACHE_DB = LOCAL_DB_DIR / "geo_cache.db"

logger = logging.getLogger("local_db_geo")

CREATE_TABLES_SQL = """
-- Кэш геокодирования
CREATE TABLE IF NOT EXISTS geo_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    name TEXT NOT NULL,
    display_name TEXT,
    address_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_geo_cache_coords ON geo_cache (lat, lon);
"""

def get_db_connection():
    conn = sqlite3.connect(GEO_CACHE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализирует БД геокодирования."""
    db_path = Path(GEO_CACHE_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("БД геокодирования инициализирована: %s", GEO_CACHE_DB)
    except Exception as e:
        logger.error("Ошибка инициализации БД геокодирования: %s", e)
        raise
    finally:
        conn.close()

# core/db/local_db_geo.py
def cache_geocoding_result(lat: float, lon: float, name: str, display_name: str, address: Dict):
    """Кэширует результат геокодирования."""
    conn = get_db_connection()
    try:
        from config.bot_config import CACHE_TTL_HOURS  # <-- Тепеь можно импортировать
        expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)

        conn.execute(
            """
            INSERT OR REPLACE INTO geo_cache
            (lat, lon, name, display_name, address_json, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (lat, lon, name, display_name, json.dumps(address, ensure_ascii=False), expires_at)
        )
        conn.commit()
        logger.debug("Кэш геокодирования сохранён: (%s, %s) -> %s", lat, lon, name)
    except Exception as e:
        logger.error("Ошибка сохранения кэша геокодирования: %s", e)
    finally:
        conn.close()
def get_cached_geocoding(lat: float, lon: float) -> Optional[Dict]:
    """Получает кэшированный результат геокодирования."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT name, display_name, address_json
            FROM geo_cache
            WHERE lat = ? AND lon = ? AND expires_at > ?
            """,
            (lat, lon, datetime.utcnow())
        )
        row = cursor.fetchone()
        if row:
            return {
                "name": row["name"],
                "display_name": row["display_name"],
                "address": json.loads(row["address_json"]) if row["address_json"] else {}
            }
        return None
    except Exception as e:
        logger.error("Ошибка получения кэша геокодирования: %s", e)
        return None
    finally:
        conn.close()

def cleanup_expired_geo_cache() -> int:
    """Удаляет устаревшие записи из кэша геокодирования."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM geo_cache WHERE expires_at <= ?",
            (datetime.utcnow(),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            logger.info("Удалено %d устаревших записей из кэша геокодирования", deleted_count)
        return deleted_count
    except Exception as e:
        logger.error("Ошибка очистки кэша геокодирования: %s", e)
        return 0
    finally:
        conn.close()