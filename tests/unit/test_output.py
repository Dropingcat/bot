# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки process_manager.
"""

import sys

def main():
    # Получаем task_id из аргументов (4-й аргумент)
    task_id = sys.argv[4] if len(sys.argv) > 4 else "unknown_task"
    
    # Импортируем логгер
    from core.utils.script_logger import get_script_logger
    logger = get_script_logger(task_id=task_id, script_name="test_output", args=sys.argv)

    try:
        logger.info("Тестовый скрипт запущен")
        
        user_id = sys.argv[3] if len(sys.argv) > 3 else "123"
        
        logger.info(f"Отправляем тестовое событие для user_id={user_id}")
        
        # Вывод для process_manager
        print("EVENT_TYPE:task_result")
        print(f"USER_ID:{user_id}")
        print("MESSAGE:Hello from subprocess!")
        
        logger.info("Тестовое событие отправлено")
        
    except Exception as e:
        logger.error(f"Ошибка в тестовом скрипте: {e}", exc_info=True)
        print("EVENT_TYPE:task_error")
        print(f"ERROR_MESSAGE:Ошибка: {e}")

if __name__ == "__main__":
    main()