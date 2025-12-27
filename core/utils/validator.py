"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Валидация данных: координаты, user_id и т.д.
"""

import re
from typing import Union


def validate_coordinates(lat: Union[str, float], lon: Union[str, float]) -> bool:
    """
    Проверяет, являются ли координаты валидными.

    Args:
        lat (float or str): Широта (-90..90)
        lon (float or str): Долгота (-180..180)

    Returns:
        bool: True, если координаты валидны
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return False

    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_user_id(user_id: Union[str, int]) -> bool:
    """
    Проверяет, является ли user_id целым положительным числом.

    Args:
        user_id (int or str): ID пользователя

    Returns:
        bool: True, если валидно
    """
    try:
        user_id = int(user_id)
        return user_id > 0
    except (ValueError, TypeError):
        return False


def validate_telegram_location(location: dict) -> bool:
    """
    Проверяет, является ли словарь location валидным (из Telegram).

    Args:
        location (dict): Словарь с ключами 'latitude', 'longitude'

    Returns:
        bool: True, если валидно
    """
    if not isinstance(location, dict):
        return False
    lat = location.get("latitude")
    lon = location.get("longitude")
    if lat is None or lon is None:
        return False
    return validate_coordinates(lat, lon)