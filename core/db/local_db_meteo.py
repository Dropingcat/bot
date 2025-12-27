# -*- coding: utf-8 -*-
"""
Локальная БД для метео- и здоровье-данных.

Таблицы:
- user_profiles: профили пользователей (гипертоник, гипотоник, чувствительный и т.д.)
- user_health_log: журнал самочувствия (АД, ЧСС, СаО2, симптомы)
- front_analysis: анализ фронтов (градиенты, ямы, ветер)
- health_impact_prediction: прогноз влияния на здоровье
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List

from config.db_config import LOCAL_DB_DIR

METEO_DB = LOCAL_DB_DIR / "meteo_cache.db"

logger = logging.getLogger("local_db_meteo")

CREATE_TABLES_SQL = """
-- Профиль пользователя
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY,
    health_category TEXT DEFAULT 'unknown',  -- 'hypertensive', 'hypotensive', 'sensitive', 'normal'
    age INTEGER,
    weight REAL,
    height REAL,
    baseline_systolic REAL,  -- базовое систолическое АД
    baseline_diastolic REAL, -- базовое диастолическое АД
    baseline_heart_rate REAL, -- базовый пульс
    baseline_spo2 REAL,       -- базовый СаО2
    baseline_symptoms TEXT,   -- json: {'migraine': 0, 'drowsiness': 0, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Журнал самочувствия
CREATE TABLE IF NOT EXISTS user_health_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    systolic REAL,      -- систолическое АД
    diastolic REAL,     -- диастолическое АД
    heart_rate INTEGER, -- ЧСС
    spo2 REAL,          -- насыщение крови кислородом
    migraine INTEGER DEFAULT 0,      -- 0-10
    drowsiness INTEGER DEFAULT 0,    -- 0-10
    anxiety INTEGER DEFAULT 0,       -- 0-10
    depression INTEGER DEFAULT 0,    -- 0-10
    excitement INTEGER DEFAULT 0,    -- 0-10
    malaise INTEGER DEFAULT 0,       -- 0-10
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Анализ фронтов
CREATE TABLE IF NOT EXISTS front_analysis (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    timestamp DATETIME NOT NULL,
    pressure_gradient REAL,      -- градиент давления
    temperature_gradient REAL,   -- градиент температуры
    wind_oscillation REAL,       -- колебания ветра
    baric_anomaly REAL,          -- аномалия давления
    front_distance_km REAL,      -- расстояние до фронта
    front_direction TEXT,        -- направление фронта
    front_type TEXT,             -- 'warm', 'cold', 'occluded', 'stationary'
    data_json TEXT,              -- все данные в JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Прогноз влияния на здоровье
CREATE TABLE IF NOT EXISTS health_impact_prediction (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    timestamp DATETIME NOT NULL,
    risk_level TEXT DEFAULT 'low',  -- 'low', 'medium', 'high', 'critical'
    risk_category TEXT,             -- 'hypertensive', 'hypotensive', 'cardio', 'oxygen', 'psycho'
    risk_comment TEXT,              -- комментарий для пользователя
    risk_score REAL,                -- 0.0 - 1.0
    forecast_json TEXT,             -- детализированный прогноз
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_user_health_log_user_id ON user_health_log (user_id);
CREATE INDEX IF NOT EXISTS idx_user_health_log_timestamp ON user_health_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_front_analysis_coords ON front_analysis (lat, lon);
CREATE INDEX IF NOT EXISTS idx_front_analysis_timestamp ON front_analysis (timestamp);
CREATE INDEX IF NOT EXISTS idx_health_impact_prediction_user_id ON health_impact_prediction (user_id);
CREATE INDEX IF NOT EXISTS idx_health_impact_prediction_timestamp ON health_impact_prediction (timestamp);
"""

def get_db_connection():
    conn = sqlite3.connect(METEO_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализирует БД метео-данных."""
    db_path = Path(METEO_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("БД метео-данных инициализирована: %s", METEO_DB)
    except Exception as e:
        logger.error("❌ Ошибка инициализации БД метео-данных: %s", e)
        raise
    finally:
        conn.close()

# === USER PROFILES ===
def save_user_profile(user_id: int, profile_data: Dict):
    """Сохраняет профиль пользователя."""
    conn = get_db_connection()
    try:
        baseline_symptoms_json = json.dumps(profile_data.get("baseline_symptoms", {}), ensure_ascii=False)
        conn.execute(
            """
            INSERT OR REPLACE INTO user_profiles
            (user_id, health_category, age, weight, height, baseline_systolic, baseline_diastolic,
             baseline_heart_rate, baseline_spo2, baseline_symptoms, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                profile_data.get("health_category"),  # <-- profile_data
                profile_data.get("age"),              # <-- profile_data
                profile_data.get("weight"),           # <-- profile_data
                profile_data.get("height"),           # <-- profile_data
                profile_data.get("baseline_systolic"),# <-- profile_data
                profile_data.get("baseline_diastolic"),# <-- profile_data
                profile_data.get("baseline_heart_rate"),# <-- profile_data
                profile_data.get("baseline_spo2"),    # <-- profile_data
                baseline_symptoms_json,               # <-- JSON строка
                datetime.utcnow()
            )
        )
        conn.commit()
        logger.info("👤 Профиль пользователя %s сохранён", user_id)
    except Exception as e:
        logger.error("❌ Ошибка сохранения профиля: %s", e)
    finally:
        conn.close()
def get_user_profile(user_id: int) -> Optional[Dict]:
    """Получает профиль пользователя."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error("❌ Ошибка получения профиля: %s", e)
        return None
    finally:
        conn.close()

# === HEALTH LOG ===
def save_user_health_log(
    user_id: int,
    timestamp: str,
    systolic: float,
    diastolic: float,
    heart_rate: int,
    spo2: float,
    migraine: int = 0,
    drowsiness: int = 0,
    anxiety: int = 0,
    depression: int = 0,
    excitement: int = 0,
    malaise: int = 0,
    comment: str = ""
):
    """Сохраняет запись в журнал самочувствия."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO user_health_log
            (user_id, timestamp, systolic, diastolic, heart_rate, spo2,
             migraine, drowsiness, anxiety, depression, excitement, malaise, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, timestamp, systolic, diastolic, heart_rate, spo2,
             migraine, drowsiness, anxiety, depression, excitement, malaise, comment)
        )
        conn.commit()
        logger.info("📊 Запись самочувствия для user %s сохранена", user_id)
    except Exception as e:
        logger.error("❌ Ошибка сохранения записи самочувствия: %s", e)
    finally:
        conn.close()

def get_user_health_log(user_id: int, start_date: str = None, end_date: str = None) -> List[Dict]:
    """Получает журнал самочувствия за период."""
    conn = get_db_connection()
    try:
        where_clause = "WHERE user_id = ?"
        params = [user_id]

        if start_date:
            where_clause += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND timestamp <= ?"
            params.append(end_date)

        cursor = conn.execute(f"SELECT * FROM user_health_log {where_clause} ORDER BY timestamp DESC", params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("❌ Ошибка получения журнала: %s", e)
        return []
    finally:
        conn.close()

def get_user_health_stats(user_id: int) -> Dict:
    """Получает статистику по самочувствию (средние значения)."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT
                AVG(systolic) as avg_systolic,
                AVG(diastolic) as avg_diastolic,
                AVG(heart_rate) as avg_heart_rate,
                AVG(spo2) as avg_spo2,
                AVG(migraine) as avg_migraine,
                AVG(drowsiness) as avg_drowsiness,
                AVG(anxiety) as avg_anxiety,
                AVG(depression) as avg_depression,
                AVG(excitement) as avg_excitement,
                AVG(malaise) as avg_malaise
            FROM user_health_log
            WHERE user_id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else {}
    except Exception as e:
        logger.error("❌ Ошибка получения статистики: %s", e)
        return {}
    finally:
        conn.close()

# === FRONT ANALYSIS ===
def save_front_analysis(lat: float, lon: float, timestamp: str, analysis_data: Dict):
    """Сохраняет анализ фронтов."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO front_analysis
            (lat, lon, timestamp, pressure_gradient, temperature_gradient, wind_oscillation,
             baric_anomaly, front_distance_km, front_direction, front_type, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lat, lon, timestamp,
                analysis_data.get("pressure_gradient"),
                analysis_data.get("temperature_gradient"),
                analysis_data.get("wind_oscillation"),
                analysis_data.get("baric_anomaly"),
                analysis_data.get("front_distance_km"),
                analysis_data.get("front_direction"),
                analysis_data.get("front_type"),
                json.dumps(analysis_data, ensure_ascii=False)
            )
        )
        conn.commit()
        logger.info("🌪️  Анализ фронтов (%s, %s) сохранён", lat, lon)
    except Exception as e:
        logger.error("❌ Ошибка сохранения анализа фронтов: %s", e)
    finally:
        conn.close()

def get_recent_front_analysis(lat: float, lon: float, hours_back: int = 24) -> List[Dict]:
    """Получает анализ фронтов в радиусе за последние N часов."""
    conn = get_db_connection()
    try:
        from datetime import datetime, timedelta
        time_limit = datetime.utcnow() - timedelta(hours=hours_back)

        cursor = conn.execute(
            """
            SELECT * FROM front_analysis
            WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
              AND timestamp > ?
            ORDER BY timestamp DESC
            """,
            (lat - 0.5, lat + 0.5, lon - 0.5, lon + 0.5, time_limit.isoformat())
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("❌ Ошибка получения анализа фронтов: %s", e)
        return []
    finally:
        conn.close()

# === HEALTH IMPACT PREDICTION ===
def save_health_impact_prediction(user_id: int, timestamp: str, prediction_data: Dict):
    """Сохраняет прогноз влияния на здоровье."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO health_impact_prediction
            (user_id, timestamp, risk_level, risk_category, risk_comment, risk_score, forecast_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, timestamp,
                prediction_data.get("risk_level"),
                prediction_data.get("risk_category"),
                prediction_data.get("risk_comment"),
                prediction_data.get("risk_score"),
                json.dumps(prediction_data.get("forecast_json", {}), ensure_ascii=False)
            )
        )
        conn.commit()
        logger.info("🩺 Прогноз влияния для user %s сохранён", user_id)
    except Exception as e:
        logger.error("❌ Ошибка сохранения прогноза: %s", e)
    finally:
        conn.close()

def get_user_health_predictions(user_id: int, start_date: str = None, end_date: str = None) -> List[Dict]:
    """Получает прогнозы влияния на здоровье за период."""
    conn = get_db_connection()
    try:
        where_clause = "WHERE user_id = ?"
        params = [user_id]

        if start_date:
            where_clause += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND timestamp <= ?"
            params.append(end_date)

        cursor = conn.execute(f"SELECT * FROM health_impact_prediction {where_clause} ORDER BY timestamp DESC", params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error("❌ Ошибка получения прогнозов: %s", e)
        return []
    finally:
        conn.close()