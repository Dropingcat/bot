"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Анализ атмосферных фронтов и их влияния.
"""

import sys
from datetime import datetime
from core.utils.script_logger import get_script_logger
from core.utils.api_client import APIClient
from scripts.meteo._processes.front_analyzer import analyze_fronts

def main():
    task_id = sys.argv[5] if len(sys.argv) > 5 else "unknown_task"
    logger = get_script_logger(task_id=task_id, script_name="front_forecast_script", args=sys.argv)

    try:
        lat = float(sys.argv[1])
        lon = float(sys.argv[2])
        user_id = int(sys.argv[3])
        radius_km = float(sys.argv[4])  # например, 100 км

        logger.info(f"Анализ фронтов для ({lat}, {lon}), user_id={user_id}")

        # Получаем сетку данных
        client = APIClient()
        results = client.get_weather_range_sync(
            start_lat=lat - 0.5, start_lon=lon - 0.5,
            end_lat=lat + 0.5, end_lon=lon + 0.5,
            step_deg=0.1, provider="open_meteo", days=1
        )

        # Анализируем фронты
        front_data = analyze_fronts(results, lat, lon)

        logger.info("Фронты проанализированы")

        # Выводим результат
        print("EVENT_TYPE:task_result")
        print("RESULT_TYPE:text")
        print(f"USER_ID:{user_id}")
        print(f"MESSAGE:Фронты: {front_data['front_distance']} км, градиент: {front_data['gradient']}")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        print("EVENT_TYPE:task_error")
        print(f"ERROR_MESSAGE:Ошибка: {e}")

if __name__ == "__main__":
    main()