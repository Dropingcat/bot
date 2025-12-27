"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Утилита для централизованной обработки ошибок.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("error_handler")


def log_and_raise(message: str, exception: Exception, context: Optional[dict] = None):
    """
    Логирует ошибку и выбрасывает её дальше.

    Args:
        message (str): Пользовательское сообщение
        exception (Exception): Исключение, которое обрабатывается
        context (dict): Дополнительный контекст (например, user_id, lat, lon)
    """
    log_context = f" | Контекст: {context}" if context else ""
    logger.error(f"{message}{log_context} | Ошибка: {exception!r}", exc_info=True)
    raise exception

def log_exception(exception: Exception, message: str = "Необработанное исключение", context: Optional[dict] = None):
    """
    Просто логирует исключение без выбрасывания.
    
    Args:
        exception (Exception): Исключение
        message (str): Описание
        context (dict): Контекст (user_id и т.п.)
    """
    log_context = f" | Контекст: {context}" if context else ""
    logger.error(f"{message}{log_context} | Ошибка: {exception!r}", exc_info=True)
def safe_call(func, *args, context: Optional[dict] = None, **kwargs):
    """
    Безопасный вызов функции с логированием ошибок.

    Args:
        func: Функция для вызова
        *args, **kwargs: Аргументы
        context (dict): Контекст для логирования

    Returns:
        Результат функции или None, если была ошибка.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_and_raise(f"Ошибка при вызове {func.__name__}", e, context)
        return None