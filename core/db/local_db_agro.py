# -*- coding: utf-8 -*-
"""
Локальная база данных для кэширования агропрогнозов.

Используется для:
- Хранения прогнозов погоды для растений
- Кэширования анализа почвы
- Прогнозов фаз роста
- Оптимизации полива/удобрений

Таблицы:
- agro_forecast_cache: кэш агропрогнозов
- soil_analysis_cache: кэш анализа почвы
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from config.db_config import AGRO_CACHE_DB

logger = logging.getLogger("local_db_agro")

# === SQL ЗАПРОСЫ ===
CREATE_TABLES_SQL = """
-- Кэш агропрогнозов
CREATE TABLE IF NOT EXISTS agro_forecast_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plant_id INTEGER,  -- может быть NULL для общего прогноза
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    timestamp DATETIME NOT NULL,
    forecast_date DATE NOT NULL,  -- дата прогноза
    forecast_type TEXT NOT NULL,  -- 'growth', 'watering', 'frost_warning'
    data_json TEXT NOT NULL,      -- прогноз (температура, влажность, риск заморозков)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Кэш анализа почвы
CREATE TABLE IF NOT EXISTS soil_analysis_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    location_id INTEGER,  -- привязка к локации
    timestamp DATETIME NOT NULL,
    analysis_type TEXT NOT NULL,  -- 'composition', 'moisture', 'ph'
    data_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agro_forecast_user_date 
ON agro_forecast_cache (user_id, forecast_date, expires_at);

CREATE INDEX IF NOT EXISTS idx_soil_analysis_user_type 
ON soil_analysis_cache (user_id, analysis_type, expires_at);
"""

# === УТИЛИТЫ ===
def get_db_connection():
    conn = sqlite3.connect(AGRO_CACHE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db_path = Path(AGRO_CACHE_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("Локальная БД агропрогноза инициализирована: %s", AGRO_CACHE_DB)
    except Exception as e:
        logger.error("Ошибка инициализации локальной БД агро: %s", e)
        raise
    finally:
        conn.close()


# === КЭШ АГРОПРОГНОЗОВ ===
def cache_agro_forecast(
    user_id: int,
    lat: float,
    lon: float,
    forecast_date: datetime,
    forecast_type: str,
    forecast_data: Dict,  # ← ПРАВИЛЬНОЕ ИМЯ АРГУМЕНТА
    plant_id: Optional[int] = None,
    ttl_hours: int = 168  # 1 неделя
) -> bool:
    """Кэширует агропрогноз."""
    conn = get_db_connection()
    try:
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        data_json = json.dumps(forecast_data, ensure_ascii=False)  # ← ИСПОЛЬЗУЕМ ПРАВИЛЬНОЕ ИМЯ

        conn.execute(
            """
            INSERT INTO agro_forecast_cache
            (user_id, plant_id, lat, lon, timestamp, forecast_date, forecast_type, data_json, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, plant_id, lat, lon, datetime.utcnow(), forecast_date.date(), forecast_type, data_json, expires_at)
        )
        conn.commit()
        logger.debug("Кэширован агропрогноз %s для пользователя %s", forecast_type, user_id)
        return True
    except Exception as e:
        logger.error("Ошибка кэширования агропрогноза: %s", e)
        return False
    finally:
        conn.close()


def get_cached_agro_forecast(
    user_id: int,
    lat: float,
    lon: float,
    forecast_date: datetime,
    forecast_type: str,
    plant_id: Optional[int] = None
) -> Optional[Dict]:
    """Получает кэшированный агропрогноз."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT data_json
            FROM agro_forecast_cache
            WHERE user_id = ? AND lat = ? AND lon = ? AND forecast_date = ? AND forecast_type = ?
              AND (plant_id = ? OR plant_id IS NULL)
              AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, lat, lon, forecast_date.date(), forecast_type, plant_id, datetime.utcnow())
        )
        row = cursor.fetchone()
        return json.loads(row["data_json"]) if row else None
    except Exception as e:
        logger.error("Ошибка получения кэша агропрогноза: %s", e)
        return None
    finally:
        conn.close()


# === КЭШ АНАЛИЗА ПОЧВЫ ===
def cache_soil_analysis(
    user_id: int,
    analysis_type: str,
    analysis_data: Dict,  # ← ПРАВИЛЬНОЕ ИМЯ АРГУМЕНТА
    location_id: Optional[int] = None,
    ttl_hours: int = 720  # 30 дней
) -> bool:
    """Кэширует анализ почвы."""
    conn = get_db_connection()
    try:
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        data_json = json.dumps(analysis_data, ensure_ascii=False)  # ← ИСПОЛЬЗУЕМ ПРАВИЛЬНОЕ ИМЯ

        conn.execute(
            """
            INSERT INTO soil_analysis_cache
            (user_id, location_id, timestamp, analysis_type, data_json, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, location_id, datetime.utcnow(), analysis_type, data_json, expires_at)
        )
        conn.commit()
        logger.debug("Кэширован анализ почвы %s для пользователя %s", analysis_type, user_id)
        return True
    except Exception as e:
        logger.error("Ошибка кэширования анализа почвы: %s", e)
        return False
    finally:
        conn.close()


def get_cached_soil_analysis(
    user_id: int,
    analysis_type: str,
    location_id: Optional[int] = None
) -> Optional[Dict]:
    """Получает кэшированный анализ почвы."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT data_json
            FROM soil_analysis_cache
            WHERE user_id = ? AND analysis_type = ?
              AND (location_id = ? OR location_id IS NULL)
              AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, analysis_type, location_id, datetime.utcnow())
        )
        row = cursor.fetchone()
        return json.loads(row["data_json"]) if row else None
    except Exception as e:
        logger.error("Ошибка получения кэша анализа почвы: %s", e)
        return None
    finally:
        conn.close()


def cleanup_expired_agro_cache() -> int:
    """Удаляет устаревшие записи из кэша агро."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM agro_forecast_cache WHERE expires_at <= ?; DELETE FROM soil_analysis_cache WHERE expires_at <= ?;",
            (datetime.utcnow(), datetime.utcnow())
        )
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            logger.info("Удалено %d устаревших записей из кэша агро", deleted_count)
        return deleted_count
    except Exception as e:
        logger.error("Ошибка очистки кэша агро: %s", e)
        return 0
    finally:
        conn.close()