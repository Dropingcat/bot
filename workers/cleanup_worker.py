# -*- coding: utf-8 -*-
"""
Воркер очистки старых файлов.
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta

logger = logging.getLogger("cleanup_worker")

async def cleanup_worker():
    """
    Удаляет старые файлы из temp/, data/, отчеты/, тесты/ каждые 10 минут.
    """
    logger.info("🧹 Cleanup worker запущен")
    
    while True:
        try:
            # === УДАЛЕНИЕ ФАЙЛОВ СТАРЕЕ 1 ДНЯ ===
            now = datetime.now()
            cutoff = now - timedelta(days=1)
            
            for folder in ["temp", "data", "отчеты", "тесты"]:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        filepath = os.path.join(folder, filename)
                        
                        # Проверяем время модификации
                        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        
                        if mod_time < cutoff:
                            try:
                                if os.path.isfile(filepath):
                                    os.remove(filepath)
                                    logger.debug(f"🗑️ Удалён файл: {filepath}")
                                elif os.path.isdir(filepath):
                                    shutil.rmtree(filepath)
                                    logger.debug(f"🗑️ Удалена папка: {filepath}")
                            except Exception as e:
                                logger.error(f"❌ Не удалось удалить {filepath}: {e}")
            
            logger.info("✅ Cleanup worker started")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
        
        # === ЖДЁМ 10 МИНУТ ===
        await asyncio.sleep(10 * 60)  # 10 минут