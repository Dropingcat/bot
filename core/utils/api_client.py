# -*- coding: utf-8 -*-
"""
Обёртка для API (Open-Meteo, ECMWF, GFS, и др.).
Поддерживает:
- Один запрос: get_weather_data(lat, lon, ...)
- Диапазон: get_weather_range(start_lat, start_lon, end_lat, end_lon, step_deg, ...)
- Ограничение одновременных запросов
- Кэширование через local_db_weather
"""
import pandas as pd
import numpy as np
import asyncio
import requests
import logging
from typing import Dict, Optional, List, Union, Tuple
from datetime import datetime, timedelta
import time

from core.db.local_db_weather import cache_weather_data, get_cached_weather
from config.bot_config import DEBUG_MODE

logger = logging.getLogger("api_client")

# === КОНФИГУРАЦИЯ API ===
API_TIMEOUT = 30  # секунд
CACHE_TTL_HOURS = 1  # кэшируем на 1 час

# === ОГРАНИЧЕНИЕ ЗАПРОСОВ ===
API_SEMAPHORE = asyncio.Semaphore(5)  # максимум 5 одновременных запросов к API
REQUEST_DELAY = 0.2  # задержка между запросами (в секундах)

class OpenMeteoClient:
    """Клиент для Open-Meteo API."""
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def get_hourly_forecast(self, lat: float, lon: float, days: int = 7) -> Optional[Dict]:
        """
        Получает почасовой прогноз от Open-Meteo.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m", "relative_humidity_2m", "precipitation_probability",
                "precipitation", "pressure_msl", "cloud_cover",
                "wind_speed_10m", "wind_direction_10m",
                "dew_point_2m", "surface_pressure", "shortwave_radiation"
            ],
            "daily": [
                "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "sunrise", "sunset", "uv_index_max"
            ],
            "timezone": "auto",
            "forecast_days": min(days, 16)
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Open-Meteo: прогноз получен для ({lat}, {lon})")
            return data
        except Exception as e:
            logger.error(f"❌ Open-Meteo: ошибка: {e}")
            return None


class GFSClient:
    """Клиент для GFS (Global Forecast System) через Open-Meteo."""
    
    def get_gfs_data(self, lat: float, lon: float, days: int = 7) -> Optional[Dict]:
        """
        Получает данные GFS через Open-Meteo (GFS Seamless).
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m", "pressure_msl", "relative_humidity_2m",
                "wind_speed_10m", "wind_direction_10m", "cape", "lifted_index",
                "precipitation", "snowfall", "visibility", "cloud_cover"
            ],
            "models": "gfs_seamless",
            "timezone": "auto",
            "forecast_days": min(days, 16)
        }

        url = "https://api.open-meteo.com/v1/gfs"
        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ GFS: данные получены для ({lat}, {lon})")
            return data
        except Exception as e:
            logger.error(f"❌ GFS: ошибка: {e}")
            return None


class ECMWFClient:
    """Клиент для ECMWF (через Open-Meteo, или ERA5 через CDS)."""
    
    def get_ecmwf_data(self, lat: float, lon: float, days: int = 7) -> Optional[Dict]:
        """
        Получает данные ECMWF через Open-Meteo (ERA5).
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m", "pressure_msl", "relative_humidity_2m",
                "wind_speed_10m", "wind_direction_10m", "cape",
                "precipitation", "snowfall", "cloud_cover"
            ],
            "models": "ecmwf_ifs04",
            "timezone": "auto",
            "forecast_days": min(days, 16)
        }

        url = "https://api.open-meteo.com/v1/ecmwf"
        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ ECMWF: данные получены для ({lat}, {lon})")
            return data
        except Exception as e:
            logger.error(f"❌ ECMWF: ошибка: {e}")
            return None


class APIClient:
    """Единый клиент для всех API."""
    
    def __init__(self):
        self.open_meteo = OpenMeteoClient()
        self.gfs = GFSClient()
        self.ecmwf = ECMWFClient()

    async def _get_weather_single(
        self,
        lat: float,
        lon: float,
        provider: str = "open_meteo",
        days: int = 7,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Внутренний метод для одного запроса.
        """
        # === ИНИЦИАЛИЗИРУЕМ БД КЭША ===
        if use_cache:
            from core.db.local_db_weather import init_db
            init_db()

        # Проверяем кэш
        if use_cache:
            cached = get_cached_weather(lat, lon, datetime.now(), source=provider)
            if cached:
                logger.info(f"💾 Кэш найден для ({lat}, {lon}) через {provider}")
                return cached

        # Ограничиваем количество одновременных запросов
        async with API_SEMAPHORE:
            # Запрашиваем API
            if provider == "open_meteo":
                data = self.open_meteo.get_hourly_forecast(lat, lon, days)
            elif provider == "gfs":
                data = self.gfs.get_gfs_data(lat, lon, days)
            elif provider == "ecmwf":
                data = self.ecmwf.get_ecmwf_data(lat, lon, days)
            else:
                logger.error(f"❌ Неизвестный провайдер: {provider}")
                return None

            # Кэшируем результат
            if data:
                cache_weather_data(
                    user_id=None,
                    lat=lat,
                    lon=lon,
                    forecast_datetime=datetime.now(),
                    data=data,
                    source=provider,
                    ttl_hours=CACHE_TTL_HOURS
                )
                logger.info(f"💾 Данные закэшированы для ({lat}, {lon}) через {provider}")

            # Задержка между запросами
            await asyncio.sleep(REQUEST_DELAY)

        return data

    def get_weather_data(
        self,
        lat: float,
        lon: float,
        provider: str = "open_meteo",
        days: int = 7,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Синхронный метод для одного запроса.
        """
        return asyncio.run(self._get_weather_single(lat, lon, provider, days, use_cache))

    async def get_weather_range(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        step_deg: float,
        provider: str = "open_meteo",
        days: int = 7,
        use_cache: bool = True
    ) -> Dict[Tuple[float, float], Optional[Dict]]:
        """
        Асинхронный метод для диапазона координат.

        Args:
            start_lat: Начальная широта
            start_lon: Начальная долгота
            end_lat: Конечная широта
            end_lon: Конечная долгота
            step_deg: Шаг сетки (например, 0.25)
            provider: "open_meteo", "gfs", "ecmwf"
            days: Количество дней
            use_cache: Использовать кэш

        Returns:
            {(lat, lon): data_dict, ...}
        """
        # === ГЕНЕРАЦИЯ СЕТКИ КООРДИНАТ ===
        lats = []
        lon = start_lon
        while lon <= end_lon:
            lats.append(lon)
            lon += step_deg

        lons = []
        lat = start_lat
        while lat <= end_lat:
            lons.append(lat)
            lat += step_deg

        # Создаём список всех точек
        coord_list = [(lat, lon) for lat in lats for lon in lons]

        logger.info(f"🌐 Запрашиваем {len(coord_list)} точек: {coord_list[:3]}...")

        # === АСИНХРОННО ЗАПРАШИВАЕМ ВСЕ ТОЧКИ ===
        tasks = [
            self._get_weather_single(lat, lon, provider, days, use_cache)
            for lat, lon in coord_list
        ]

        results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        # === СОБИРАЕМ РЕЗУЛЬТАТ ===
        results = {}
        for i, (lat, lon) in enumerate(coord_list):
            res = results_raw[i]
            if isinstance(res, Exception):
                logger.error(f"❌ Ошибка в точке ({lat}, {lon}): {res}")
                results[(lat, lon)] = None
            else:
                results[(lat, lon)] = res

        return results

    def get_weather_range_sync(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        step_deg: float,
        provider: str = "open_meteo",
        days: int = 7,
        use_cache: bool = True
    ) -> Dict[Tuple[float, float], Optional[Dict]]:
        """
        Синхронная версия для диапазона.
        """
        return asyncio.run(
            self.get_weather_range(
                start_lat, start_lon, end_lat, end_lon, step_deg,
                provider, days, use_cache
            )
        )

    def validate_input(
        self,
        lat: Union[float, None] = None,
        lon: Union[float, None] = None,
        start_lat: Union[float, None] = None,
        start_lon: Union[float, None] = None,
        end_lat: Union[float, None] = None,
        end_lon: Union[float, None] = None,
        step_deg: Union[float, None] = None
    ) -> bool:
        """
        Валидация входных данных.
        """
        # Проверяем, что задан либо один запрос, либо диапазон
        is_single = lat is not None and lon is not None
        is_range = all(v is not None for v in [start_lat, start_lon, end_lat, end_lon, step_deg])

        if not is_single and not is_range:
            logger.error("❌ Неверный формат входных данных: должны быть указаны либо (lat, lon), либо (start_lat, start_lon, end_lat, end_lon, step_deg)")
            return False

        if is_single and is_range:
            logger.error("❌ Неверный формат: нельзя одновременно указать одиночные и диапазонные координаты")
            return False

        # Валидация координат
        if is_single:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                logger.error(f"❌ Неверные координаты: lat={lat}, lon={lon}")
                return False

        if is_range:
            if not all(-90 <= v <= 90 for v in [start_lat, end_lat]) or \
               not all(-180 <= v <= 180 for v in [start_lon, end_lon]):
                logger.error(f"❌ Неверный диапазон: start_lat={start_lat}, start_lon={start_lon}, end_lat={end_lat}, end_lon={end_lon}")
                return False
            if step_deg <= 0:
                logger.error(f"❌ Шаг должен быть положительным: step_deg={step_deg}")
                return False

        return True


    def get_gfs_turbulence_data_sync(self, lat: float, lon: float, hours: int = 24) -> pd.DataFrame:
        """
        Запрос данных GFS Seamless для расчёта турбулентности.
        """
        print("🔄 Запрос данных GFS Seamless для расчёта турбулентности...")
        lat = round(lat, 4)
        lon = round(lon, 4)

        # Уровни давления (список, не строка!)
        levels_list = [1000, 925, 850, 700, 500, 400, 300, 250]

        # Формируем список параметров для каждого уровня
        hourly_params = []
        for level in levels_list:  # ← итерация по числам, а не строке
            hourly_params.extend([
                f"temperature_{level}hPa",
                f"vertical_velocity_{level}hPa",
                f"geopotential_height_{level}hPa",
                f"wind_direction_{level}hPa",
                f"wind_speed_{level}hPa",
            ])

        # Собираем в строку
        hourly_str = ",".join(hourly_params)

        # URL для GFS Seamless
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"model=gfs_seamless&"
            f"hourly={hourly_str}&"
            f"forecast_days={min(7, (hours // 24) + 1)}&timezone=auto"
        )
        print(f"   URL: {url}")
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ GFS Seamless API error: {response.status_code}")
            print(response.text)
            raise Exception(f"GFS API error: {response.status_code}, {response.text}")

        data = response.json()

        # АВАРИЙНЫЙ ДАМП — всегда показываем ответ
        print("🔍 Ответ от GFS Seamless:")
        try:
            import json
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(data)

        # Безопасное извлечение
        if 'hourly' not in data:
            raise RuntimeError("Ключ 'hourly' отсутствует в ответе API.")

        hourly = data['hourly']
        time = pd.to_datetime(hourly['time'])
        n_times = len(time)

        # Словарь для хранения данных по уровням
        level_data = {}
        for level in levels_list:
            level_data[level] = {
                'temp': np.array(hourly[f'temperature_{level}hPa']),
                'vvel': np.array(hourly[f'vertical_velocity_{level}hPa']),
                'gph': np.array(hourly[f'geopotential_height_{level}hPa']),
                'wdir': np.array(hourly[f'wind_direction_{level}hPa']),
                'wspd': np.array(hourly[f'wind_speed_{level}hPa']),
            }

        # Вычисляем компоненты ветра (u, v) из направления и скорости
        for level in levels_list:
            wdir_rad = np.deg2rad(level_data[level]['wdir'])
            wspd = level_data[level]['wspd']
            level_data[level]['u'] = -wspd * np.sin(wdir_rad)  # u = -wspd * sin(wdir)
            level_data[level]['v'] = -wspd * np.cos(wdir_rad)  # v = -wspd * cos(wdir)

        # Вычисляем N_turb по часам
        N_turb = np.full(n_times, np.nan)
        for t in range(n_times):
            # Массивы для текущего времени
            z_levels = np.array([level_data[l]['gph'][t] for l in levels_list])
            theta_levels = np.array([
                level_data[l]['temp'][t] * ((1000.0 / l)**0.286) for l in levels_list  # theta = T * (1000/P)^0.286
            ])
            u_levels = np.array([level_data[l]['u'][t] for l in levels_list])
            v_levels = np.array([level_data[l]['v'][t] for l in levels_list])

            # Вычисляем градиенты
            dz = np.diff(z_levels)
            dtheta_dz = np.diff(theta_levels) / dz
            du_dz = np.diff(u_levels) / dz
            dv_dz = np.diff(v_levels) / dz

            # N^2
            g = 9.81
            theta_avg = (theta_levels[1:] + theta_levels[:-1]) / 2
            N_squared = (g / theta_avg) * dtheta_dz

            # S^2
            S_squared = du_dz**2 + dv_dz**2

            # Richardson Number
            Ri = N_squared / (S_squared + 1e-10)  # защита от деления на 0

            # Усреднённый Ri (например, минимальный — наиболее турбулентный слой)
            Ri_min = np.min(Ri)

            # N_turb = 1 / Ri_min (чем меньше Ri, тем выше турбулентность)
            N_turb[t] = 1.0 / max(Ri_min, 0.01) if Ri_min > 0 else 0.0

        # Создаём DataFrame
        df = pd.DataFrame({
            'time': time,
            'N_turb': N_turb,
        })

        # Ограничиваем количество строк по часам
        df = df.head(hours)

        # Заполняем NaN
        df['N_turb'] = df['N_turb'].fillna(method='ffill').fillna(method='bfill')

        print(f"✅ Получено {len(df)} часов данных турбулентности.")
        return df

# === УДОБНЫЕ ФУНКЦИИ ===
def get_weather_forecast(lat: float, lon: float, provider: str = "open_meteo") -> Optional[Dict]:
    """Удобная функция для получения прогноза в одной точке."""
    client = APIClient()
    return client.get_weather_data(lat, lon, provider)

def get_weather_forecast_range(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    step_deg: float,
    provider: str = "open_meteo"
) -> Dict[Tuple[float, float], Optional[Dict]]:
    """Удобная функция для получения прогноза по сетке."""
    client = APIClient()
    return client.get_weather_range_sync(start_lat, start_lon, end_lat, end_lon, step_deg, provider)