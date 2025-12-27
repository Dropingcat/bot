# -*- coding: utf-8 -*-
"""
Шина событий (Event Bus) для межмодульного взаимодействия.

Архитектурный принцип:
- Производители (process_manager, скрипты через stdout) → публикуют события
- Потребители (бот, воркеры) → подписываются на события
- event_bus.py НЕ импортирует bot.py, scripts/, workers/ — зависимости только в одну сторону

Использование:

# В bot.py (потребитель):
from core.event_bus import subscribe_async

async def on_task_result(event):
    await bot.send_message(event["user_id"], event["message"])

subscribe_async("task_result", on_task_result)

# В process_manager.py (производитель):
from core.event_bus import emit_event

await emit_event("task_result", {"user_id": 123, "message": "Готово!"})
"""

import asyncio
from typing import Dict, List, Callable, Any, Union, Awaitable # <-- Добавлен Awaitable
import logging

# Настройка логгера
logger = logging.getLogger("event_bus")

# Типы обработчиков
SyncHandler = Callable[[Dict[str, Any]], None]
# AsyncHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]  # <-- Старая строка
AsyncHandler = Callable[[Dict[str, Any]], Awaitable[None]] # <-- Исправленная строка

# Реестры обработчиков
_sync_handlers: Dict[str, List[SyncHandler]] = {}
_async_handlers: Dict[str, List[AsyncHandler]] = {}


def subscribe(event_type: str, handler: SyncHandler) -> None:
    """
    Подписка на событие с синхронным обработчиком.
    
    Args:
        event_type (str): Тип события (например, "task_result")
        handler (callable): Функция, принимающая dict с данными события
    """
    if event_type not in _sync_handlers:
        _sync_handlers[event_type] = []
    _sync_handlers[event_type].append(handler)
    logger.debug("Зарегистрирован синхронный обработчик для события: %s", event_type)

def unsubscribe_async(event_type: str, handler: AsyncHandler) -> None:
    """
    Отписка от события.
    """
    if event_type in _async_handlers:
        try:
            _async_handlers[event_type].remove(handler)
            logger.debug("Обработчик удалён для события: %s", event_type)
        except ValueError:
            logger.warning("Обработчик не найден для события: %s", event_type)
def subscribe_async(event_type: str, handler: AsyncHandler) -> None:
    """
    Подписка на событие с асинхронным обработчиком.
    
    Args:
        event_type (str): Тип события (например, "task_complete")
        handler (callable): Асинхронная функция, принимающая dict с данными события
    """
    if handler is None:
        logger.warning(f"⚠️ Попытка подписаться на событие {event_type} с handler=None. Игнорируем.")
        return
    if event_type not in _async_handlers:
        _async_handlers[event_type] = []
    _async_handlers[event_type].append(handler)
    logger.debug("Зарегистрирован асинхронный обработчик для события: %s", event_type)


async def emit_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Асинхронная публикация события.
    
    Вызывает все зарегистрированные обработчики (синхронные и асинхронные).
    Ошибки в обработчиках логируются, но не прерывают выполнение.
    
    Args:
        event_type (str): Тип события
        event_data (dict): Данные события (рекомендуется включать "user_id" при наличии)
    """
    logger.debug("Публикация события: %s, данные: %s", event_type, event_data)
    
    # Выполнение синхронных обработчиков в потоке executor'а (чтобы не блокировать event loop)
    if event_type in _sync_handlers:
        for handler in _sync_handlers[event_type]:
            current_handler = handler  # === ЗАПОМИНАЕМ handler ===
            if current_handler is not None:  # === ПРОВЕРЯЕМ ===
                try:
                    # Запускаем синхронный обработчик в отдельном потоке
                    await asyncio.get_event_loop().run_in_executor(None, current_handler, event_data)
                except Exception as e:
                    logger.error("Ошибка в синхронном обработчике события %s: %s", event_type, e, exc_info=True)
    
    # Выполнение асинхронных обработчиков
    if event_type in _async_handlers:
        for handler in _async_handlers[event_type]:
            current_handler = handler  # === ЗАПОМИНАЕМ handler ===
            if current_handler is not None:  # === ПРОВЕРЯЕМ ===
                try:
                    await current_handler(event_data)  # === ИСПОЛЬЗУЕМ КОПИЮ ===
                except Exception as e:
                    logger.error("Ошибка в асинхронном обработчике события %s: %s", event_type, e, exc_info=True)
def emit_event_sync(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Синхронная публикация события (для использования в subprocess-скриптах через IPC).
    
    ⚠️ ВАЖНО: Эта функция НЕ вызывает асинхронные обработчики!
    Она предназначена ТОЛЬКО для случаев, когда event_bus доступен в том же процессе,
    но нет event loop (например, при тестировании или в специальных IPC-сценариях).
    
    В основном проекте используйте emit_event() из process_manager.py.
    """
    logger.debug("Синхронная публикация события: %s", event_type)
    
    if event_type in _sync_handlers:
        for handler in _sync_handlers[event_type]:
            try:
                handler(event_data)
            except Exception as e:
                logger.error("Ошибка в синхронном обработчике (sync): %s", e, exc_info=True)
    else:
        logger.warning("Нет синхронных обработчиков для события: %s", event_type)


# Утилита для очистки (полезна в тестах)
def clear_all_handlers() -> None:
    """Очищает все зарегистрированные обработчики. Используется в тестах."""
    _sync_handlers.clear()
    _async_handlers.clear()
    logger.info("Все обработчики событий очищены.")