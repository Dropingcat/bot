# -*- coding: utf-8 -*-
"""
Конфигурация логирования проекта.
Соответствует структуре папки logs/.
"""

import logging
import logging.config
from pathlib import Path
import os

from core.utils.log_filter import EmojiFilter, UnicodeSafeFormatter

# Путь к папке логов
LOGS_DIR = Path(__file__).parent.parent / "logs"

# Уровни логирования
LOG_LEVEL = "DEBUG" if bool(os.getenv("DEBUG_MODE", False)) else "INFO"

# Формат сообщений (без эмодзи)
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-15s | %(funcName)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Убедимся, что папка логов существует
LOGS_DIR.mkdir(exist_ok=True)

# Создаём фильтр
emoji_filter = EmojiFilter()

# Конфигурация логгера
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": LOG_FORMAT,
            "datefmt": DATE_FORMAT,
        },
    },
    "filters": {
        "emoji_filter": {
            "()": lambda: emoji_filter  # передаём фильтр
        }
    },
    "handlers": {
        "default": {
            "level": LOG_LEVEL,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "filters": ["emoji_filter"]  # применяем фильтр
        },
        "file_app": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "app.log",
            "encoding": "utf-8",
            "filters": ["emoji_filter"]  # применяем фильтр
        },
        "file_error": {
            "level": "ERROR",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "errors.log",
            "encoding": "utf-8",
            "filters": ["emoji_filter"]  # применяем фильтр
        },
        "file_debug": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "debug.log",
            "encoding": "utf-8",
            "filters": ["emoji_filter"]  # применяем фильтр
        },
    },
    "loggers": {
        "": {  # корневой логгер
            "handlers": ["default", "file_app", "file_error"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "debug": {
            "handlers": ["file_debug"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Применяем конфиг
logging.config.dictConfig(LOGGING_CONFIG)

# Экспортируем удобный доступ к логгерам
app_logger = logging.getLogger("app")
error_logger = logging.getLogger("error")
debug_logger = logging.getLogger("debug")