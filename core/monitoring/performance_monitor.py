"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Мониторинг производительности.
"""

import logging
import time

logger = logging.getLogger("performance_monitor")

def monitor_performance(func):
    """
    Декоратор для измерения времени выполнения функции.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"⏱️ {func.__name__} took {end_time - start_time:.2f} seconds")
        return result
    return wrapper