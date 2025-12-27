"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Конфигурация Telegram-бота.
Использует переменные окружения из .env файла.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env файл (если он есть)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# === ОСНОВНЫЕ НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
"""Токен Telegram-бота. Обязательно задать в .env файле."""

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "yes")
"""Режим отладки: подробные логи, тестовые данные, отключение rate-лимитов."""

ADMIN_USER_IDS = [
    int(uid.strip()) for uid in os.getenv("ADMIN_USER_IDS", "").split(",") if uid.strip()
]
"""Список ID администраторов (через запятую в .env)."""

# === ПУТИ К ФАЙЛАМ ===
PROJECT_ROOT = Path(__file__).parent.parent
"""Корневая директория проекта."""

DATA_DIR = PROJECT_ROOT / "data"
"""Папка для сохранения графиков, HTML-отчётов и временных файлов."""

TEMP_DIR = PROJECT_ROOT / "temp"
"""Папка для кэша и промежуточных данных."""

LOGS_DIR = PROJECT_ROOT / "logs"
"""Папка для логов."""

# === ПОВЕДЕНИЕ БОТА ===
DEFAULT_FORECAST_DAYS = 7
"""Количество дней в прогнозе по умолчанию."""

MAX_SAVED_LOCATIONS = 10
"""Максимальное количество сохранённых локаций на пользователя."""

GEOLOCATION_TIMEOUT_SEC = 30
"""Таймаут ожидания геопозиции от пользователя (секунды)."""
# === КЭШИРОВАНИЕ ===
CACHE_TTL_HOURS = 24 * 30  # 30 дней
"""Время жизни кэша в часах."""
# === ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ ПАРАМЕТРОВ ===
if not BOT_TOKEN:
    raise RuntimeError(
        "❌ Переменная окружения BOT_TOKEN не задана. "
        "Создайте файл .env в корне проекта и добавьте туда BOT_TOKEN=ваш_токен"
    )

# Создаём директории, если не существуют
DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)