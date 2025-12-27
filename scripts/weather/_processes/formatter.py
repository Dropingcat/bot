"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Форматирование погодного отчёта (график, текст).
"""

import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from core.utils.coordinate_manager import get_location_name
import logging

logger = logging.getLogger("formatter")

def format_weather_report(interpolated_data: dict, lat: float, lon: float) -> dict:
    """
    Формирует отчёт: график, текст, сводка.

    Args:
        interpolated_data (dict): Интерполированные данные
        lat (float): Широта
        lon (float): Долгота

    Returns:
        dict: {"plot": matplotlib.figure, "summary": str, "location_name": str}
    """
    try:
        times = interpolated_data["time"]
        temp = interpolated_data["temperature_2m"]
        pressure = interpolated_data["pressure_msl"]
        humidity = interpolated_data["relative_humidity_2m"]

        # === 1. СОЗДАНИЕ ГРАФИКА ===
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

        # Температура
        ax1.plot(times, temp, label="Температура (°C)", color="red")
        ax1.set_ylabel("Темп. (°C)")
        ax1.grid(True)
        ax1.legend()

        # Давление
        ax2.plot(times, pressure, label="Давление (гПа)", color="blue")
        ax2.set_ylabel("Давление (гПа)")
        ax2.grid(True)
        ax2.legend()

        # Влажность
        ax3.plot(times, humidity, label="Влажность (%)", color="green")
        ax3.set_ylabel("Влажность (%)")
        ax3.set_xlabel("Время")
        ax3.grid(True)
        ax3.legend()

        fig.suptitle(f"Прогноз погоды для ({lat}, {lon})")
        plt.xticks(rotation=45)
        plt.tight_layout()

        # === 2. ТЕКСТОВАЯ СВОДКА ===
        avg_temp = np.nanmean(temp)
        avg_pressure = np.nanmean(pressure)
        avg_humidity = np.nanmean(humidity)
        summary = f"Сегодня {avg_temp:.1f}°C, давление {avg_pressure:.1f} гПа, влажность {avg_humidity:.1f}%."

        # === 3. НАЗВАНИЕ МЕСТА ===
        location_name = get_location_name(lat, lon)

        logger.info(f"✅ Отчёт сформирован для ({lat}, {lon})")
        return {
            "plot": fig,
            "summary": summary,
            "location_name": location_name
        }

    except Exception as e:
        logger.error(f"❌ Ошибка форматирования: {e}", exc_info=True)
        return None