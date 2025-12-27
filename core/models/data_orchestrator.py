# -*- coding: utf-8 -*-
"""
Оркестратор данных — централизованно управляет запросами к API и БД,
и запускает модели в нужном порядке без взаимных вызовов.

Принцип:
- Собирает все необходимые данные (метео, профиль, растения) за один проход
- Кэширует в local_db_*
- Запускает модели в зависимости от их требований
- Модели не общаются друг с другом напрямую
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from core.db.central_db import get_or_create_user_profile, get_user_locations, get_user_plants
from core.db.local_db_weather import cache_weather_data, get_cached_weather
from core.db.local_db_meteo import cache_meteo_impact, cache_front_analysis
from core.db.local_db_atmosphere import cache_atmosphere_data
from core.db.local_db_agro import cache_agro_forecast, cache_soil_analysis
from core.utils.coordinate_manager import get_user_coordinates_for_task
from core.utils.api_client import OpenMeteoClient  # или твой fetcher
from core.models.meteo_model import run_meteo_model
from core.models.health_predictor import run_health_predictor
from core.models.agro_model import run_agro_model
from core.event_bus import emit_event

logger = logging.getLogger("data_orchestrator")

class DataOrchestrator:
    def __init__(self):
        self.client = OpenMeteoClient()

    async def fetch_and_cache_all_data(
        self,
        user_id: int,
        lat: float,
        lon: float,
        start_date: datetime,
        end_date: datetime
    ):
        """
        Собирает и кэширует все необходимые данные для моделей.
        """
        logger.info("🔄 Запрос и кэширование данных для %s (%s, %s)", user_id, lat, lon)

        # === 1. Погода (из Open-Meteo) ===
        weather_data = await self.client.get_hourly_forecast(lat, lon, start_date, end_date)
        for entry in weather_data:
            cache_weather_data(
                user_id, lat, lon, entry["datetime"], entry["data"], ttl_hours=24
            )

        # === 2. Метео-влияния (на основе погоды) ===
        stress_index = self._compute_stress_index(weather_data)
        cache_meteo_impact(user_id, lat, lon, start_date, "stress_index", {"value": stress_index}, ttl_hours=48)

        # === 3. Фронты (если есть) ===
        front_analysis = self._analyze_fronts(weather_data)
        if front_analysis:
            cache_front_analysis(lat, lon, start_date, front_analysis, ttl_hours=24)

        # === 4. Атмосфера (лунная фаза и т.п.) ===
        atmosphere_data = self._get_atmosphere_data(lat, lon, start_date)
        cache_atmosphere_data(lat, lon, "moon_phase", start_date, atmosphere_data, ttl_hours=168)

        logger.info("✅ Все данные закэшированы для %s", user_id)

    def _compute_stress_index(self, weather_data: List[Dict]) -> float:
        # Вставь сюда логику из твоего compute_stress_index
        # norm_dP_dt, norm_dT_dt, norm_front, norm_shear, norm_turb, norm_rad, norm_dRH_dt
        # weights = [0.2, 0.1, 0.25, 0.2, 0.05, 0.1, 0.1]
        # stress_index = np.dot(stress_vector, weights)
        # return np.clip(stress_index, 0, 1)
        return 0.5  # Заглушка

    def _analyze_fronts(self, weather_ List[Dict]) -> Optional[Dict]:
        # Вставь сюда логику из fetch_gfs_turbulence_data или анализа фронтов
        return {"front_type": "cold", "strength": 0.8, "distance_km": 100.0}

    def _get_atmosphere_data(self, lat: float, lon: float, date: datetime) -> Dict:
        # Вставь сюда расчёт фазы луны и т.п.
        return {"phase": "full_moon", "illumination": 0.99}

    async def run_models_for_user(self, user_id: int, location_id: Optional[int] = None):
        """
        Запускает все модели для пользователя в нужном порядке.
        """
        # 1. Получаем координаты
        coords = get_user_coordinates_for_task(user_id, location_id)
        if not coords:
            logger.error("❌ Не удалось получить координаты для %s", user_id)
            return
        lat, lon = coords

        # 2. Получаем профиль пользователя
        profile = get_or_create_user_profile(user_id)

        # 3. Определяем диапазон дат
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)

        # 4. Собираем и кэшируем все данные
        await self.fetch_and_cache_all_data(user_id, lat, lon, start_date, end_date)

        # 5. Запускаем модели в нужном порядке
        # Метео -> Здоровье -> Агро

        # --- Запуск meteo_model ---
        logger.info("🚀 Запуск meteo_model для %s", user_id)
        meteo_result = await run_meteo_model(user_id, lat, lon, start_date, end_date)
        if meteo_result:
            await emit_event("meteo_analysis_ready", {
                "user_id": user_id,
                "lat": lat,
                "lon": lon,
                "result": meteo_result
            })

        # --- Запуск health_predictor ---
        logger.info("🚀 Запуск health_predictor для %s", user_id)
        health_result = await run_health_predictor(user_id, lat, lon, start_date, end_date, profile)
        if health_result:
            await emit_event("health_prediction_ready", {
                "user_id": user_id,
                "lat": lat,
                "lon": lon,
                "result": health_result
            })

        # --- Запуск agro_model ---
        logger.info("🚀 Запуск agro_model для %s", user_id)
        plants = get_user_plants(user_id)  # из central_db
        agro_result = await run_agro_model(user_id, lat, lon, start_date, end_date, plants)
        if agro_result:
            await emit_event("agro_recommendations_ready", {
                "user_id": user_id,
                "lat": lat,
                "lon": lon,
                "result": agro_result
            })

        logger.info("✅ Все модели выполнены для %s", user_id)