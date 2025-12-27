"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Проверка состояния системы.
"""

import logging
from core.db.local_db_meteo import init_db as init_meteo_db
from core.db.local_db_weather import init_db as init_weather_db

logger = logging.getLogger("health_checker")

def health_check():
    """
    Проверяет основные компоненты.
    """
    try:
        # Проверка БД
        init_meteo_db()
        init_weather_db()
        logger.info("✅ Health check passed")
        return True
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False