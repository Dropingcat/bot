"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Получение данных погоды через api_client.
"""

from core.utils.api_client import APIClient
import logging

logger = logging.getLogger("data_fetcher")

def fetch_weather_data(lat: float, lon: float, days: int = 1) -> dict:
    """
    Получает погодные данные.

    Args:
        lat (float): Широта
        lon (float): Долгота
        days (int): Количество дней

    Returns:
        dict: Данные или None
    """
    client = APIClient()
    data = client.get_weather_data(lat, lon, provider="open_meteo", days=days)
    if data:
        logger.info(f"✅ Данные получены для ({lat}, {lon})")
        return data
    else:
        logger.error(f"❌ Не удалось получить данные для ({lat}, {lon})")
        return None