# -*- coding: utf-8 -*-
"""
Логгер для скриптов, запускаемых через process_manager.

Использует общую конфигурацию логирования из logging_config.py,
но добавляет контекст: task_id, script_name, args.
"""

import logging
import sys
from pathlib import Path
import os

# === ПОДГРУЖАЕМ КОНФИГУРАЦИЮ ЛОГИРОВАНИЯ, ЕСЛИ НЕ ЗАГРУЖЕНА ===
if not logging.getLogger().hasHandlers():
    from config.logging_config import LOGGING_CONFIG
    import logging.config
    logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger("script_logger")

# === КОНТЕКСТНЫЙ ФОРМАТТЕР ===
class ContextFormatter(logging.Formatter):
    def format(self, record):
        # Добавляем контекст, если он есть
        task_id = getattr(record, 'task_id', 'N/A')
        script_name = getattr(record, 'script_name', 'N/A')
        args = getattr(record, 'args_str', 'N/A')
        
        record.task_id = task_id
        record.script_name = script_name
        record.args_str = args
        
        return super().format(record)

def get_script_logger(task_id: str = "N/A", script_name: str = "unknown", args: list = None):
    """
    Возвращает логгер с контекстом для скрипта.

    Пример:
        logger = get_script_logger(task_id, __file__, sys.argv)
        logger.info("Начинаю обработку...")
    """
    args_str = ':'.join(args) if args else 'N/A'
    
    # Создаём "дочерний" логгер с контекстом
    child_logger = logging.getLogger(f"script_logger.{script_name}")

    # Убедимся, что у него есть handlers
    if not child_logger.hasHandlers():
        from config.logging_config import LOGS_DIR
        formatter = ContextFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | "
            "[TASK:%(task_id)s | SCRIPT:%(script_name)s | ARGS:%(args_str)s] | %(message)s"
        )

        handler_app = logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")
        handler_app.setFormatter(formatter)
        handler_app.setLevel(logging.INFO)

        handler_error = logging.FileHandler(LOGS_DIR / "errors.log", encoding="utf-8")
        handler_error.setFormatter(formatter)
        handler_error.setLevel(logging.ERROR)

        child_logger.addHandler(handler_app)
        child_logger.addHandler(handler_error)
        child_logger.setLevel(logging.DEBUG)

    # Добавляем фильтр, чтобы вставлять контекст в каждое сообщение
    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.task_id = task_id
            record.script_name = script_name
            record.args_str = args_str
            return True

    child_logger.addFilter(ContextFilter())
    return child_logger