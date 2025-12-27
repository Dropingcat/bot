"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Интерполяция погодных данных.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from core.utils.data_processor import interpolate_timeseries
import logging

logger = logging.getLogger("interpolator")

def interpolate_weather_data(raw_data: dict) -> dict:
    """
    Интерполирует погодные данные (температура, давление, влажность и т.д.).

    Args:
        raw_data (dict): Ответ от api_client

    Returns:
        dict: Интерполированные данные
    """
    try:
        hourly = raw_data.get("hourly", {})
        time_list = hourly.get("time", [])
        if not time_list:
            logger.error("❌ В данных отсутствуют временные метки")
            return None

        # Извлекаем основные параметры
        temp = hourly.get("temperature_2m", [])
        pressure = hourly.get("pressure_msl", [])
        humidity = hourly.get("relative_humidity_2m", [])
        cloud_cover = hourly.get("cloud_cover", [])
        wind_speed = hourly.get("wind_speed_10m", [])
        wind_dir = hourly.get("wind_direction_10m", [])

        # Интерполируем данные с шагом 1 час
        target_times = pd.date_range(start=time_list[0], end=time_list[-1], freq='1h').strftime('%Y-%m-%d %H:%M:%S').tolist()

        interpolated = {
            "time": target_times,
            "temperature_2m": interpolate_timeseries(time_list, temp, target_times),
            "pressure_msl": interpolate_timeseries(time_list, pressure, target_times),
            "relative_humidity_2m": interpolate_timeseries(time_list, humidity, target_times),
            "cloud_cover": interpolate_timeseries(time_list, cloud_cover, target_times),
            "wind_speed_10m": interpolate_timeseries(time_list, wind_speed, target_times),
            "wind_direction_10m": interpolate_timeseries(time_list, wind_dir, target_times),
            "forecast_datetime": datetime.now()
        }

        logger.info(f"✅ Интерполяция выполнена: {len(time_list)} → {len(target_times)} точек")
        return interpolated

    except Exception as e:
        logger.error(f"❌ Ошибка интерполяции: {e}", exc_info=True)
        return None