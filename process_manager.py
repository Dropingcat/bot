# process_manager.py
# -*- coding: utf-8 -*-
"""
Глобальный координатор зависимостей.
Инициализирует все сервисы один раз и предоставляет к ним доступ.
"""

import os
from typing import Optional
from pathlib import Path
import logging
from config.bot_config import BotConfig
from core.utils.validator import sanitize_user_input
from core.db.central_db import CentralDB  # ← НОВОЕ
from config.db_config import CENTRAL_DB_PATH  # ← для явного указания пути (опционально)
from config.logging_config import setup_logging 
class ProcessManager:
    """
    Единый контекст приложения. Все зависимости инициализируются здесь.
    """

    def __init__(self):
        self._initialized = False
        # Конфигурация
        self.config: Optional[BotConfig] = None
        # Базы данных
        self.central_db: Optional[CentralDB] = None  # ← НОВОЕ
        # Утилиты
        self.sanitize_user_input = sanitize_user_input
        self.use_simulator = os.getenv("USE_SIMULATOR", "false").lower() == "true"
        
    def initialize_sync(self):
        """Синхронная инициализация всех компонентов."""
        if self._initialized:
            return

        # 1. Загрузка конфигурации
        self.config = BotConfig.load()

        # 2. Инициализация центральной БД
        self.central_db = CentralDB(db_path=CENTRAL_DB_PATH)

        self._initialized = True
        print("✅ ProcessManager: initialized (central_db ready)")

    def shutdown_sync(self):
        """Синхронное завершение (закрытие ресурсов)."""
        if not self._initialized:
            return

        # Центральная БД SQLite не требует явного закрытия (соединения локальные),
        # но можно добавить логику очистки, если потребуется.
        print("🛑 Processanager: shut down")

# Глобальный экземпляр — точка доступа для всех модулей
process_manager = ProcessManager()