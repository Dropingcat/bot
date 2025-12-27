# Документация: Использование `api_client.py`

## Обзор

`api_client.py` — это **универсальный клиент** для получения метеоданных из:
- Open-Meteo
- GFS (Global Forecast System)
- ECMWF (European Centre for Medium-Range Weather Forecasts)

Поддерживает:
- **Одиночные запросы** — `(lat, lon)`
- **Диапазонные запросы** — сетка точек `start_lat, start_lon, end_lat, end_lon, step_deg`
- **Кэширование** через `local_db_weather`
- **Защиту от перегрузки API**
- **Валидацию входных данных**

---

## 1. Импорт

```python
from core.utils.api_client import APIClient, get_weather_forecast, get_weather_forecast_range

2. Основные функции
2.1. get_weather_forecast(lat, lon, provider="open_meteo")
Получить прогноз в одной точке.

Параметры:

lat (float): Широта (-90..90)
lon (float): Долгота (-180..180)
provider (str): "open_meteo", "gfs", "ecmwf" (по умолчанию "open_meteo")
Возвращает:

dict — данные прогноза
None — при ошибке
Пример:

python
12345
data = get_weather_forecast(55.75, 37.62, "open_meteo")
if data:
    print("✅ Прогноз получен")
else:
    print("❌ Ошибка получения прогноза")
2.2. get_weather_forecast_range(...)
Получить прогноз по сетке точек.

Параметры:

start_lat (float): Начальная широта
start_lon (float): Начальная долгота
end_lat (float): Конечная широта
end_lon (float): Конечная долгота
step_deg (float): Шаг сетки (например, 0.25)
provider (str): "open_meteo", "gfs", "ecmwf"
Возвращает:

Dict[(lat, lon): data, ...] — словарь с координатами и данными
None — при ошибке
Пример:

python
1234567891011121314
results = get_weather_forecast_range(
    start_lat=55.0,
    start_lon=37.0,
    end_lat=56.0,
    end_lon=38.0,
    step_deg=0.25,
    provider="open_meteo"
)

for (lat, lon), data in results.items():

3. Использование в скриптах
3.1. В scripts/weather/weather_today_script.py
python
1234567891011121314151617
import sys
from core.utils.api_client import get_weather_forecast

def main():
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])
    user_id = int(sys.argv[3])

    data = get_weather_forecast(lat, lon, "open_meteo")
    if data:

3.2. В scripts/weather/baric_map_daily_script.py
python
123456789101112131415161718192021222324
import sys
from core.utils.api_client import get_weather_forecast_range

def main():
    start_lat = float(sys.argv[1])
    start_lon = float(sys.argv[2])
    end_lat = float(sys.argv[3])
    end_lon = float(sys.argv[4])
    step = float(sys.argv[5])
    user_id = int(sys.argv[6])

4. Валидация входных данных
Координаты: lat ∈ [-90, 90], lon ∈ [-180, 180]
Шаг: step_deg > 0
Можно указать либо (lat, lon) либо (start_lat, start_lon, end_lat, end_lon, step_deg)