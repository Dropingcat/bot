# -*- coding: utf-8 -*-
"""
Скрипт прогноза погоды на сегодня.
"""

import sys
from pathlib import Path
from datetime import datetime # Убедитесь, что импортировано в начале файла

cache_timestamp = datetime.now()

# Добавляем путь к проекту, если нужно
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.utils.script_logger import get_script_logger

def main():
    # task_id передаётся как 4-й аргумент
    task_id = sys.argv[4] if len(sys.argv) > 4 else "unknown_task"
    logger = get_script_logger(task_id=task_id, script_name="weather_today_script", args=sys.argv)

    try:
        logger.info("🚀 Запуск скрипта прогноза погоды")
        
        lat, lon, user_id = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
        logger.info(f"🌍 Получены параметры: lat={lat}, lon={lon}, user_id={user_id}")
        
        # === ВАША ЛОГИКА ===
        from scripts.weather._processes.data_fetcher import fetch_weather_data
        from scripts.weather._processes.interpolator import interpolate_weather_data
        from scripts.weather._processes.formatter import format_weather_report
        from core.utils.cache_manager import save_plot
        from core.db.local_db_weather import cache_weather_data

        raw_data = fetch_weather_data(lat, lon, days=1)
        if not raw_data:
            logger.error("❌ Не удалось получить данные погоды")
            print("EVENT_TYPE:task_error")
            print("ERROR_MESSAGE:Не удалось получить данные погоды")
            return

        interpolated_data = interpolate_weather_data(raw_data)
        if not interpolated_data:
            logger.error("❌ Ошибка интерполяции")
            print("EVENT_TYPE:task_error")
            print("ERROR_MESSAGE:Ошибка интерполяции данных")
            return

        report = format_weather_report(interpolated_data, lat, lon)
        if not report:
            logger.error("❌ Ошибка форматирования отчёта")
            print("EVENT_TYPE:task_error")
            print("ERROR_MESSAGE:Ошибка форматирования отчёта")
            return

        graph_path = save_plot(report['plot'], prefix=f"weather_{user_id}_{int(lat*1000)}_{int(lon*1000)}")
        logger.info(f"🖼️  График сохранён: {graph_path}")

        cache_weather_data(
            user_id=user_id,
            lat=lat,
            lon=lon,
            forecast_datetime=interpolated_data.get("forecast_datetime"),
            data=interpolated_data,
            source="open_meteo",
        )
        logger.info("💾 Данные закэшированы")

        logger.info("✅ Обработка завершена")
        
        # Вывод для process_manager
        print("EVENT_TYPE:task_result")
        print("RESULT_TYPE:graph")
        print(f"USER_ID:{user_id}")
        print(f"FILE_PATH:{graph_path}")
        print(f"SUMMARY:{report['summary']}")
        print(f"LOCATION_NAME:{report['location_name']}")

    except Exception as e:
        logger.error(f"💥 Ошибка в скрипте: {e}", exc_info=True)
        print("EVENT_TYPE:task_error")
        print(f"ERROR_MESSAGE:Ошибка: {e}")

if __name__ == "__main__":
    main()