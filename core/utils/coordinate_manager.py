# -*- coding: utf-8 -*-
"""
Менеджер координат и геокодирования.

Функции:
- Получение названия места по координатам (reverse geocoding)
- Валидация координат
- Кэширование через local_db_geo или pickle-файл
- Обработка ошибок API (Nominatim)

Использование:
>>> from core.utils.coordinate_manager import get_location_name
>>> name = get_location_name(55.75, 37.62)
>>> print(name)
'Москва, Россия'
"""

import requests
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import hashlib

from core.db.local_db_geo import init_db, cache_geocoding_result, get_cached_geocoding
from config.bot_config import DEBUG_MODE

logger = logging.getLogger("coordinate_manager")

# === КОНФИГУРАЦИЯ ===
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
REQUEST_TIMEOUT = 10  # секунд
CACHE_TTL_HOURS = 24 * 30  # 30 дней

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Проверяет, что координаты в допустимом диапазоне.

    Args:
        lat (float): Широта (-90 .. 90)
        lon (float): Долгота (-180 .. 180)

    Returns:
        bool: True, если координаты корректны
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180

def reverse_geocode_nominatim(lat: float, lon: float) -> Optional[Dict]:
    """
    Получает название места по координатам через Nominatim.

    Args:
        lat (float): Широта
        lon (float): Долгота

    Returns:
        Optional[Dict]: Ответ от Nominatim или None при ошибке
    """
    if not validate_coordinates(lat, lon):
        logger.error(f"❌ Неверные координаты: lat={lat}, lon={lon}")
        return None

    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
        "accept-language": "ru,en"
    }

    headers = {
        "User-Agent": "MeteorologicalBot/1.0 (contact@yourdomain.com)"
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Извлечение названия
        address = data.get("address", {})
        name = (
            address.get("name") or
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("county") or
            address.get("state") or
            address.get("country") or
            f"Точка ({lat:.4f}, {lon:.4f})"
        )

        result = {
            "name": name,
            "display_name": data.get("display_name", name),
            "address": address,
            "lat": float(data.get("lat")),
            "lon": float(data.get("lon"))
        }

        logger.info(f"🌍 Название места: {result['name']}")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка геокодирования (Nominatim): {e}")
        return None
    except (KeyError, ValueError, AttributeError) as e:
        logger.error(f"❌ Ошибка обработки ответа Nominatim: {e}")
        return None

def get_location_name(lat: float, lon: float, use_cache: bool = True) -> str:
    """
    Возвращает название места по координатам (с кэшированием).

    Args:
        lat (float): Широта
        lon (float): Долгота
        use_cache (bool): Использовать кэш

    Returns:
        str: Название места или "Точка (lat, lon)"
    """
    # === ВАЛИДАЦИЯ ===
    if not validate_coordinates(lat, lon):
        logger.warning(f"⚠️  Неверные координаты: lat={lat}, lon={lon}")
        return f"Точка ({lat:.4f}, {lon:.4f})"

    # === ИНИЦИАЛИЗАЦИЯ БД КЭША ===
    init_db()

    # === ПРОВЕРКА КЭША ===
    if use_cache:
        cached = get_cached_geocoding(lat, lon)
        if cached:
            logger.info(f"💾 Кэш найден: {cached['name']}")
            return cached["name"]

    # === ЗАПРОС К API ===
    result = reverse_geocode_nominatim(lat, lon)
    if result:
        # === КЭШИРОВАНИЕ ===
        cache_geocoding_result(lat, lon, result["name"], result["display_name"], result["address"])
        return result["name"]

    # === ОШИБКА ===
    fallback_name = f"Точка ({lat:.4f}, {lon:.4f})"
    logger.warning(f"🌍 Название не найдено, используем: {fallback_name}")
    return fallback_name

def get_address_details(lat: float, lon: float) -> Optional[Dict]:
    """
    Возвращает детали адреса (город, улица, страна и т.д.).

    Args:
        lat (float): Широта
        lon (float): Долгота

    Returns:
        Optional[Dict]: Адрес или None
    """
    result = reverse_geocode_nominatim(lat, lon)
    return result.get("address") if result else None

def bulk_reverse_geocode(coordinates_list: list[tuple[float, float]]) -> Dict[tuple[float, float], str]:
    """
    Групповой обратный геокодинг для списка координат.

    Args:
        coordinates_list (list): [(lat, lon), ...]

    Returns:
        Dict[(lat, lon): name, ...]
    """
    results = {}
    for lat, lon in coordinates_list:
        name = get_location_name(lat, lon)
        results[(lat, lon)] = name
    return results

# === УДОБНЫЕ ФУНКЦИИ ===
def get_city_name(lat: float, lon: float) -> str:
    """Получить только город."""
    details = get_address_details(lat, lon)
    return details.get("city") or details.get("town") or details.get("village") or "Неизвестный город"

def get_country_name(lat: float, lon: float) -> str:
    """Получить только страну."""
    details = get_address_details(lat, lon)
    return details.get("country") or "Неизвестная страна"