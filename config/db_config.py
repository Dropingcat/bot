"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Конфигурация путей к базам данных проекта.
Используется как синхронно (sqlite3), так и асинхронно (aiosqlite).
"""

from pathlib import Path
import sys

# === Корень проекта ===
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# === Папка данных ===
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

LOCAL_DB_DIR = DATA_DIR / "local_db"
LOCAL_DB_DIR.mkdir(exist_ok=True)

# === ЦЕНТРАЛЬНАЯ БАЗА: пользователи и локации ===
CENTRAL_DB_PATH = DATA_DIR / "central.db"

# === ЛОКАЛЬНЫЕ КЭШИ ===
WEATHER_CACHE_DB = LOCAL_DB_DIR / "weather_cache.db"
METEO_CACHE_DB = LOCAL_DB_DIR / "meteo_cache.db"
ATMOSPHERE_CACHE_DB = LOCAL_DB_DIR / "atmosphere_cache.db"
AGRO_CACHE_DB = LOCAL_DB_DIR / "agro_cache.db"

# === ЛОГ ЗАДАЧ (опционально) ===
PROCESS_LOG_DB_PATH = DATA_DIR / "process_log.db"

# === ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ ===
DB_CONNECTION_TIMEOUT = 30  # секунд
DB_MAX_RETRIES = 3
DB_RETRY_DELAY_SEC = 1

# === TTL для кэша ===
WEATHER_CACHE_TTL_HOURS = 24
METEO_CACHE_TTL_HOURS = 48
ATMOSPHERE_CACHE_TTL_HOURS = 168  # 1 неделя
AGRO_CACHE_TTL_HOURS = 168

# === Вспомогательные функции ===
def get_sqlite_uri(db_path: Path) -> str:
    """
    Возвращает URI для SQLite, совместимый с Windows и SQLAlchemy.
    Пример: 'sqlite:///C:/bots/data/central.db'
    """
    if sys.platform == "win32":
        # На Windows нужно три слэша после sqlite:// и прямые слэши
        return f"sqlite:///{db_path.as_posix()}"
    else:
        return f"sqlite:///{db_path}"