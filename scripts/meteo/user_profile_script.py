# -*- coding: utf-8 -*-
"""
Скрипт ввода данных самочувствия пользователя с привязкой к погоде.
"""

import sys
from pathlib import Path

# === ДОБАВЛЯЕМ КОРЕНЬ ПРОЕКТА В PYTHONPATH ===
project_root = Path(__file__).parent.parent.parent  # scripts/meteo/../.. = project_root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json
from datetime import datetime
from core.utils.script_logger import get_script_logger
from core.db.local_db_meteo import save_user_health_log, get_user_health_log, get_user_health_stats
from core.db.local_db_weather import get_cached_weather, cache_weather_data
from core.utils.api_client import APIClient

def main():
    task_id = sys.argv[13] if len(sys.argv) > 13 else "unknown_task"
    logger = get_script_logger(task_id=task_id, script_name="user_profile_script", args=sys.argv)

    try:
        # === ПАРАМЕТРЫ ===
        user_id = int(sys.argv[1])
        timestamp = sys.argv[2]  # ISO format
        lat = float(sys.argv[3])
        lon = float(sys.argv[4])
        systolic = float(sys.argv[5])
        diastolic = float(sys.argv[6])
        heart_rate = int(sys.argv[7])
        spo2 = float(sys.argv[8])
        migraine = int(sys.argv[9])      # 0-10
        drowsiness = int(sys.argv[10])   # 0-10
        anxiety = int(sys.argv[11])      # 0-10
        depression = int(sys.argv[12])   # 0-10
        excitement = int(sys.argv[13])   # 0-10
        malaise = int(sys.argv[14])      # 0-10
        comment = sys.argv[15] if len(sys.argv) > 15 else ""

        logger.info(f"[USER:{user_id}] Data received for {timestamp}")

        # === ПОЛУЧЕНИЕ ПОГОДЫ ===
        weather_data = get_cached_weather(lat, lon, datetime.fromisoformat(timestamp.replace('Z', '+00:00')), source="open_meteo")
        if not weather_data:
            logger.info("[WEATHER] Not found in cache, requesting from API...")
            client = APIClient()
            raw_data = client.get_weather_data(lat, lon, provider="open_meteo", days=1)
            if raw_data:
                # Сохраняем в кэш
                cache_weather_data(
                    user_id=user_id,
                    lat=lat,
                    lon=lon,
                    forecast_datetime=datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                    data=raw_data,
                    source="open_meteo",
                    ttl_hours=24
                )
                weather_data = raw_data
            else:
                logger.warning("[WEATHER] Failed to get weather")
                weather_data = {}

        # === СОХРАНЕНИЕ САМОЧУВСТВИЯ ===
        save_user_health_log(
            user_id=user_id,
            timestamp=timestamp,
            systolic=systolic,
            diastolic=diastolic,
            heart_rate=heart_rate,
            spo2=spo2,
            migraine=migraine,
            drowsiness=drowsiness,
            anxiety=anxiety,
            depression=depression,
            excitement=excitement,
            malaise=malaise,
            comment=comment
        )

        # === ВЫВОД (ТОЛЬКО print, БЕЗ СМАЙЛИКОВ) ===
        weather_summary = f"Pressure: {weather_data.get('pressure_msl', [0])[0] if 'pressure_msl' in weather_data else 'N/A'} hPa"
        print("EVENT_TYPE:task_result")
        print("RESULT_TYPE:text")
        print(f"USER_ID:{user_id}")
        print(f"MESSAGE:Data saved for {timestamp}. Weather: {weather_summary}")

    except Exception as e:
        logger.error(f"[ERROR] {e}", exc_info=True)
        print("EVENT_TYPE:task_error")
        print(f"ERROR_MESSAGE:Error: {e}")

if __name__ == "__main__":
    main()