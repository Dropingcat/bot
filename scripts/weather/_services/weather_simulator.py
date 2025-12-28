# scripts/weather/_services/weather_simulator.py
from datetime import datetime, timedelta
from core.models.weather_response import WeatherForecast, WeatherPoint
import random

def simulate_weather_today(location_name: str) -> WeatherForecast:
    """Симулирует прогноз на сегодня: сейчас, +2ч, +6ч, +12ч."""
    now = datetime.now()
    base_temp = 5 + random.randint(-10, 20)  # температура от -5 до 25
    
    points = []
    for hours in [0, 2, 6, 12]:
        temp = base_temp + random.uniform(-3, 3)
        desc = random.choice(["Солнечно", "Пасмурно", "Дождь", "Снег", "Туман"])
        points.append(WeatherPoint(
            timestamp=now + timedelta(hours=hours),
            temp=round(temp, 1),
            description=desc
        ))
    
    return WeatherForecast(location_name=location_name, points=points)