# -*- coding: utf-8 -*-
"""
Воркер проверки здоровья системы.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from core.db.local_db_meteo import init_db as init_meteo_db
from core.db.local_db_weather import init_db as init_weather_db
from core.utils.api_client import APIClient

logger = logging.getLogger("health_check_worker")

async def health_check_worker():
    """
    Проверяет БД, API каждые 5 минут.
    """
    logger.info("🔧 Health check worker запущен")
    
    while True:
        try:
            # === ПРОВЕРКА БАЗ ДАННЫХ ===
            logger.debug("🔍 Проверка БД...")
            init_meteo_db()
            init_weather_db()
            logger.debug("✅ БД OK")
            
            # === ПРОВЕРКА API ===
            logger.debug("🔍 Проверка API...")
            client = APIClient()
            # Проверим, можно ли получить данные
            try:
                # Пробный запрос (синхронный)
                sample_data = client.get_weather_data(
                    lat=55.75, lon=37.62, provider="open_meteo", days=1
                )
                if sample_data:
                    logger.debug("✅ API OK")
                else:
                    logger.warning("⚠️ API: нет данных")
            except Exception as e:
                logger.error(f"❌ API: {e}")
            
            logger.info("✅ Health check passed")
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
        
        # === ЖДЁМ 5 МИНУТ ===
        await asyncio.sleep(5 * 60)  # 5 минут