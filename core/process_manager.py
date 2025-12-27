# -*- coding: utf-8 -*-
"""
Менеджер выполнения задач (Process Manager).
Запускает скрипты из директории scripts/ в изолированных subprocess,
парсит их вывод, отправляет результат через event_bus.
Поддерживает ограничение количества параллельных задач, таймауты и повторы.
Использование:
# В bot.py:
from core.process_manager import enqueue_script
await enqueue_script("scripts/weather/weather_today_script.py", [str(lat), str(lon), str(user_id)])

# Скрипт выводит:
# EVENT_TYPE:task_result
# RESULT_TYPE:graph
# FILE_PATH:/path/to/graph.png
# MESSAGE:Прогноз погоды на сегодня
# USER_ID:123
"""

import asyncio
import subprocess
import sys
import os
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from core.event_bus import emit_event
from core.db.process_log_db import log_task_start, log_task_finish

logger = logging.getLogger("process_manager")

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (исправлено) ===
_semaphore: Optional[asyncio.Semaphore] = None
_active_tasks: Dict[str, asyncio.Task] = {}
_TASK_QUEUE: asyncio.Queue = asyncio.Queue()
_TASK_STATUS: Dict[str, str] = {}  # running, finished, failed
_TASK_RETRIES: Dict[str, int] = {}

# === КОНФИГУРАЦИЯ (из process_config.py или константы) ===
MAX_CONCURRENT_TASKS = 2
TASK_TIMEOUT_SEC = 300  # 5 минут
TASK_MAX_RETRIES = 3
TASK_RETRY_DELAY_SEC = 2

# === ИНИЦИАЛИЗАЦИЯ (вызов через bot.py) ===
async def _start_workers():
    """Запускает внутренние worker'ы process_manager."""
    global _semaphore
    _semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    logger.info(f"🚀 Запуск воркеров process_manager (max_concurrent={MAX_CONCURRENT_TASKS})")
    # Запускаем бесконечный цикл обработки очереди
    asyncio.create_task(_process_queue_loop())

async def _process_queue_loop():
    """Бесконечный цикл обработки задач из очереди."""
    while True:
        task_item = await _TASK_QUEUE.get()
        asyncio.create_task(_execute_task_with_semaphore(task_item))
        _TASK_QUEUE.task_done()

def init_process_manager():
    """Инициализирует process_manager (запускает worker'ы)."""
    asyncio.create_task(_start_workers())
    logger.info("✅ Process manager инициализирован")

# === ФУНКЦИИ УПРАВЛЕНИЯ ===
async def enqueue_script(script_path: str, args: list[str], retries_left: int = None) -> str:
    """
    Добавляет задачу в очередь на выполнение.
    Возвращает уникальный task_id.
    """
    if retries_left is None:
        retries_left = TASK_MAX_RETRIES

    task_id = hashlib.md5(f"{script_path}{''.join(args)}{datetime.utcnow().isoformat()}".encode()).hexdigest()
    _TASK_STATUS[task_id] = "pending"
    _TASK_RETRIES[task_id] = retries_left

    # Логируем в БД
    log_task_start(task_id, script_path, args)

    # Помещаем в очередь
    await _TASK_QUEUE.put({
        "task_id": task_id,
        "script_path": script_path,
        "args": args,
        "retries_left": retries_left
    })

    logger.info(f"✅ Задача {task_id} добавлена в очередь: {script_path} с аргументами {args}")
    return task_id

def get_active_task_count() -> int:
    """Возвращает количество активных задач."""
    # Считаем только те, у кого статус "running"
    return sum(1 for status in _TASK_STATUS.values() if status == "running")


# === ВНУТРЕННЯЯ ЛОГИКА ВЫПОЛНЕНИЯ ===
async def _execute_task_with_semaphore(task_item: Dict):
    """Обертка для выполнения задачи с ограничением по количеству."""
    async with _semaphore:
        await _execute_task(task_item)

async def _execute_task(task_item: Dict):
    """Выполняет одну задачу с изоляцией и логированием."""
    task_id = task_item["task_id"]
    script_path_str = task_item["script_path"]
    args = task_item["args"]
    retries_left = task_item["retries_left"]

    # Обновляем статус
    _TASK_STATUS[task_id] = "running"

    logger.info(f"🚀 Выполняем задачу {task_id}: {script_path_str} с аргументами {args}")

    # --- ИСПРАВЛЕНИЕ 1: УКАЗЫВАЕМ PYTHONPATH ---
    project_root = Path(__file__).parent.parent.parent  # core/process_manager/../.. = project_root
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    # --- ИСПРАВЛЕНИЕ 2: ПЕРЕДАЁМ task_id как 4-й аргумент ---
    full_args = [sys.executable, script_path_str, *args, task_id]

    try:
        # --- ИСПРАВЛЕНИЕ 6: ЗАПУСК КАК ФАЙЛ, А НЕ КАК МОДУЛЬ ---
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *full_args, # Вместо sys.executable, "-m", module_name, *args, task_id
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                env=env # <-- ПЕРЕДАЁМ env С PYTHONPATH
            ),
            timeout=TASK_TIMEOUT_SEC
        )
    except asyncio.TimeoutError:
        logger.error("❌ Таймаут выполнения задачи %s", task_id)
        # --- ИСПРАВЛЕНИЕ 5: ОПРЕДЕЛЯЕМ error_msg ---
        error_msg = f"❌ Таймаут выполнения (>{TASK_TIMEOUT_SEC} сек)"
        await _handle_task_failure(task_id, script_path_str, args, error_msg, retries_left)
        return
    except Exception as e:
        logger.error("❌ Ошибка запуска subprocess для задачи %s: %s", task_id, e)
        # --- ИСПРАВЛЕНИЕ 5: ОПРЕДЕЛЯЕМ error_msg ---
        error_msg = f"❌ Ошибка запуска subprocess: {e}"
        await _handle_task_failure(task_id, script_path_str, args, error_msg, retries_left)
        return

    # --- ИСПРАВЛЕНИЕ: Декодирование stdout и stderr с обработкой ошибок ---
    stdout_bytes, stderr_bytes = await proc.communicate()

    # Декодируем stdout
    try:
        stdout_str = stdout_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            stdout_str = stdout_bytes.decode('cp1251') # Windows-1251 как альтернатива
        except UnicodeDecodeError:
            stdout_str = stdout_bytes.decode('utf-8', errors='replace') # Заменить неверные символы

    # Декодируем stderr
    try:
        stderr_str = stderr_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            stderr_str = stderr_bytes.decode('cp1251') # Windows-1251 как альтернатива
        except UnicodeDecodeError:
            stderr_str = stderr_bytes.decode('utf-8', errors='replace') # Заменить неверные символы

    # Логируем stderr, если он есть
    if stderr_str:
        logger.error(f"STDERR задачи {task_id}: {stderr_str}")


    if proc.returncode == 0:
        logger.info(f"✅ Процесс задачи {task_id} завершён успешно (код {proc.returncode})")
        # --- ПАРСИНГ ВЫВОДА ---
        logger.debug(f"STDOUT задачи {task_id}: {stdout_str}")
        parsed_data = _parse_script_output(stdout_str)
        if parsed_data:
            # --- ОТПРАВКА СОБЫТИЯ ---
            parsed_data["task_id"] = task_id
            # Пытаемся получить user_id из аргументов для события
            user_id = args[2] if len(args) >= 3 else None
            parsed_data["user_id"] = user_id
            await emit_event("task_result", parsed_data)
            logger.info(f"📤 Событие task_result отправлено для задачи {task_id}")
        else:
            logger.warning(f"⚠️ Скрипт задачи {task_id} не вернул ожидаемых данных в stdout.")

        # Логируем завершение в БД
        log_task_finish(task_id, status="finished")
        _TASK_STATUS[task_id] = "finished"

    else:
        logger.error(f"❌ Процесс задачи {task_id} завершён с кодом {proc.returncode}")
        # --- ИСПРАВЛЕНИЕ 5: ОПРЕДЕЛЯЕМ error_msg с обработкой ошибок при декодировании ---
        # Используем уже декодированную строку stderr_str
        error_msg = f"Процесс завершился с кодом {proc.returncode}. STDERR: {stderr_str if stderr_str else 'N/A'}"
        await _handle_task_failure(task_id, script_path_str, args, error_msg, retries_left)


async def _handle_task_failure(task_id: str, script_path: str, args: list[str], error_msg: str, retries_left: int):
    """Обрабатывает ошибку выполнения задачи."""
    # --- ИСПРАВЛЕНИЕ 5: ОБЕРНЁМ В try/except ---
    try:
        logger.error(f"❌ Ошибка выполнения задачи {task_id}: {error_msg}")
        log_task_finish(task_id, status="failed", error=error_msg)

        if retries_left > 0:
            logger.info(f"🔄 Повтор задачи {task_id}, осталось: {retries_left - 1}")
            await asyncio.sleep(TASK_RETRY_DELAY_SEC)
            # Уменьшаем retries_left и снова ставим в очередь
            await enqueue_script(script_path, args, retries_left - 1)
        else:
            logger.error(f"❌ Все попытки для задачи {task_id} исчерпаны. Отправляем событие ошибки.")
            user_id = args[2] if len(args) >= 3 else None
            await emit_event("task_error", {
                "task_id": task_id,
                "EVENT_TYPE": "task_error",
                "RESULT_TYPE": "error",
                "ERROR_MESSAGE": f"❌ Ошибка выполнения: {error_msg}",
                "user_id": user_id
            })
            _TASK_STATUS[task_id] = "failed"
    except Exception as e_inner:
        logger.error(f"💥 Критическая ошибка в _handle_task_failure для задачи {task_id}: {e_inner}", exc_info=True)
        # Обновляем статус, даже если _handle_task_failure сломался
        _TASK_STATUS[task_id] = "failed"


def _parse_script_output(output: str) -> Dict[str, str]:
    """Парсит stdout скрипта на предмет строк в формате KEY:VALUE."""
    parsed = {}
    for line in output.splitlines():
        # --- ИСПРАВЛЕНИЕ: ИГНОРИРУЕМ СТРОКИ, НЕ ПОХОЖИЕ НА KEY:VALUE ---
        if ":" in line and not line.startswith("[") and not line.startswith(" "):
            try:
                key, value = line.split(":", 1) # Разделяем только на первом ":"
                parsed[key.strip()] = value.strip()
            except ValueError:
                # Если строка не подходит под KEY:VALUE, просто пропускаем
                continue
    return parsed

# --- КОНТЕКСТНЫЙ МЕНЕДЖЕР (ОПЦИОНАЛЬНО) ---
# Если планируется использовать как `async with ProcessManager() as pm:`
# class ProcessManager:
#     async def __aenter__(self):
#         await _start_workers()
#         return self
#     async def __aexit__(self, exc_type, exc, tb):
#         # Очистка ресурсов
#         pass