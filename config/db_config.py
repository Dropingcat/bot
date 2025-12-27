# -*- coding: utf-8 -*-
"""
Конфигурация баз данных проекта.
"""

from pathlib import Path

# === ЦЕНТРАЛЬНАЯ БАЗА ДАННЫХ (пользователи, локации) ===
CENTRAL_DB_PATH = Path(__file__).parent.parent / "data" / "central.db"
"""Путь к SQLite-файлу центральной БД."""

CENTRAL_DB_URL = f"sqlite:///{CENTRAL_DB_PATH.as_posix()}"
"""URL подключения к центральной БД (для SQLAlchemy, если потребуется)."""

# === ЛОКАЛЬНЫЕ БАЗЫ ДАННЫХ (кэш по модулям) ===
LOCAL_DB_DIR = Path(__file__).parent.parent / "data" / "local_db"
"""Папка для локальных баз данных (кэш погоды, метео и т.д.)."""

# Создаём папку для локальных БД
LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)

# Пути к конкретным локальным БД (можно использовать напрямую или через URL)
WEATHER_CACHE_DB = LOCAL_DB_DIR / "weather_cache.db"
METEO_CACHE_DB = LOCAL_DB_DIR / "meteo_cache.db"
METEO_DB = LOCAL_DB_DIR / "meteo_cache.db"  
ATMOSPHERE_CACHE_DB = LOCAL_DB_DIR / "atmosphere_cache.db"
AGRO_CACHE_DB = LOCAL_DB_DIR / "agro_cache.db"

# --- ДОБАВЛЕНО: БАЗА ДАННЫХ ЛОГА ЗАДАЧ PROCESS MANAGER ---
PROCESS_LOG_DB_PATH = Path(__file__).parent.parent / "data" / "process_log.db"
"""Путь к SQLite-файлу лога задач process_manager."""

# === НАСТРОЙКИ ПОДКЛЮЧЕНИЙ ===
DB_CONNECTION_TIMEOUT = 30  # секунд
DB_MAX_RETRIES = 3
DB_RETRY_DELAY_SEC = 1

# === TTL для кэша (время жизни записей) ===
WEATHER_CACHE_TTL_HOURS = 24
METEO_CACHE_TTL_HOURS = 48
ATMOSPHERE_CACHE_TTL_HOURS = 168  # 1 неделя
AGRO_CACHE_TTL_HOURS = 168