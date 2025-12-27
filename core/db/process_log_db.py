# -*- coding: utf-8 -*-
"""
Модуль для логирования задач процесс-менеджера в отдельную БД.
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from config.db_config import PROCESS_LOG_DB_PATH  # Убедись, что этот путь определён в config

def init_db():
    """Инициализирует таблицу task_log в базе данных."""
    os.makedirs(os.path.dirname(PROCESS_LOG_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(PROCESS_LOG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_log (
            task_id TEXT PRIMARY KEY,
            script_path TEXT NOT NULL,
            arguments TEXT, -- JSON строка
            start_time TEXT,
            end_time TEXT,
            status TEXT, -- 'running', 'finished', 'failed'
            error_message TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_task_start(task_id: str, script_path: str, args: list):
    """Логирует начало задачи."""
    conn = sqlite3.connect(PROCESS_LOG_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO task_log (task_id, script_path, arguments, start_time, status) VALUES (?, ?, ?, ?, ?)",
            (task_id, script_path, json.dumps(args), datetime.now().isoformat(), 'running')
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Ошибка логирования старта задачи: {e}")
    finally:
        conn.close()

def log_task_finish(task_id: str, status: str = 'finished', error: str = None):
    """Логирует завершение задачи."""
    conn = sqlite3.connect(PROCESS_LOG_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE task_log SET end_time = ?, status = ?, error_message = ? WHERE task_id = ?",
            (datetime.now().isoformat(), status, error, task_id)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"❌ Ошибка логирования завершения задачи: {e}")
    finally:
        conn.close()

def get_task_status(task_id: str) -> dict:
    """
    Получает статус задачи из БД.
    Возвращает словарь с полями: task_id, status, start_time, end_time, error_message.
    Если задача не найдена, возвращает None.
    """
    conn = sqlite3.connect(PROCESS_LOG_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT task_id, status, start_time, end_time, error_message FROM task_log WHERE task_id = ?",
            (task_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "task_id": row[0],
                "status": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "error_message": row[4]
            }
        return None
    except sqlite3.Error as e:
        print(f"❌ Ошибка получения статуса задачи: {e}")
        return None
    finally:
        conn.close()

# --- Пример использования ---
# if __name__ == "__main__":
#     init_db()
#     tid = "test_task_123"
#     log_task_start(tid, "script.py", ["arg1", "arg2"])
#     import time; time.sleep(2)
#     log_task_finish(tid, status="finished")
#     status_info = get_task_status(tid)
#     print(status_info)