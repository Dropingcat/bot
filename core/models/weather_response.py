"""Module placeholder."""
# core/models/weather_response.py
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class WeatherPoint:
    timestamp: datetime
    temp: float
    description: str

@dataclass
class WeatherForecast:
    location_name: str
    points: List[WeatherPoint]  # [0h, 2h, 6h, 12h]