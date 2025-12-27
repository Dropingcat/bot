"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Скрипт добавления локации.
"""

import sys
from core.db.central_db import add_user_location
from core.utils.script_logger import get_script_logger

def main():
    task_id = sys.argv[4] if len(sys.argv) > 4 else "unknown_task"
    logger = get_script_logger(task_id=task_id, script_name="add_location_script", args=sys.argv)

    try:
        logger.info("Запуск скрипта добавления локации")
        
        user_id, lat, lon, name = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        logger.info(f"Параметры: user_id={user_id}, lat={lat}, lon={lon}, name={name}")
        
        # === ВАША ЛОГИКА ===
        location_id = add_user_location(user_id, name, lat, lon)
        
        if location_id:
            logger.info(f"Локация добавлена с ID: {location_id}")
            print("EVENT_TYPE:task_result")
            print("RESULT_TYPE:notification")
            print(f"USER_ID:{user_id}")
            print(f"MESSAGE:✅ Локация '{name}' добавлена!")
        else:
            logger.warning("Локация не добавлена (возможно, дубль)")
            print("EVENT_TYPE:task_result")
            print("RESULT_TYPE:notification")
            print(f"USER_ID:{user_id}")
            print("MESSAGE:⚠️ Локация уже существует")
        
    except Exception as e:
        logger.error(f"Ошибка добавления локации: {e}", exc_info=True)
        print("EVENT_TYPE:task_error")
        print(f"ERROR_MESSAGE:Ошибка: {e}")

if __name__ == "__main__":
    main()