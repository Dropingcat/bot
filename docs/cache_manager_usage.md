# Cache Manager — документация

## Обзор

`cache_manager.py` — это **универсальный инструмент** для **сохранения и загрузки файлов** в папку `data/`.

Используется для:
- Сохранения **графиков** (matplotlib, PIL)
- Сохранения **данных** (JSON, CSV)
- Сохранения **отчётов** (HTML)
- **Кэширования** временных файлов
- **Очистки** старых файлов

---

## Установка

Ничего не требуется — `cache_manager` использует стандартные библиотеки Python и `matplotlib`, `PIL` (если используются).

---

## Импорт

```python
from core.utils.cache_manager import (
    save_plot,
    save_json,
    save_csv,
    save_html,
    load_json,
    get_recent_files,
    cleanup_old_files
)

Функции
1. save_plot(data, filename=None, prefix="plot")
Сохраняет график (matplotlib или PIL Image).

Параметры:

data — matplotlib.figure.Figure или PIL.Image
filename — имя файла (если None, генерируется автоматически)
prefix — префикс для автогенерации
Возвращает: str — путь к файлу

Пример:

python
123456
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 2])
path = save_plot(fig, prefix="weather_graph")
print(f"График сохранён: {path}")
2. save_json(data, filename=None, prefix="data")
Сохраняет словарь как JSON.

Параметры:

data — dict для сохранения
filename — имя файла (если None, генерируется автоматически)
prefix — префикс для автогенерации
Возвращает: str — путь к файлу

Пример:

python
123
data = {"temperature": [1, 2, 3], "humidity": [40, 50, 60]}
path = save_json(data, prefix="forecast")
print(f"JSON сохранён: {path}")
3. save_csv(data, headers=None, filename=None, prefix="data")
Сохраняет данные как CSV.

Параметры:

data — list списков или list словарей
headers — заголовки (опционально)
filename — имя файла (если None, генерируется автоматически)
prefix — префикс для автогенерации
Возвращает: str — путь к файлу

Пример:

python
1234
data = [[1, 2], [3, 4]]
headers = ["X", "Y"]
path = save_csv(data, headers=headers, prefix="coords")
print(f"CSV сохранён: {path}")
4. save_html(content, filename=None, prefix="report")
Сохраняет HTML-страницу.

Параметры:

content — строка с HTML
filename — имя файла (если None, генерируется автоматически)
prefix — префикс для автогенерации
Возвращает: str — путь к файлу

Пример:

python
123
html = "<html><body><h1>Отчёт</h1></body></html>"
path = save_html(html, prefix="weather_report")
print(f"HTML сохранён: {path}")
5. load_json(filename)
Загружает JSON из data/.

Параметры:

filename — имя файла
Возвращает: dict или None

Пример:

python
12345
data = load_json("forecast_xxx.json")
if 
    print("Данные загружены")
else:
    print("Файл не найден")
6. get_recent_files(ext=None, limit=10)
Получает последние файлы из data/.

Параметры:

ext — расширение (например, "png", "json") — если None, все
limit — количество файлов
Возвращает: list[str] — список имён файлов

Пример:

python
12
recent = get_recent_files(ext="png", limit=5)
print(f"Последние PNG: {recent}")
7. cleanup_old_files(ext=None, keep_last_n=20)
Удаляет старые файлы, оставляя последние N.

Параметры:

ext — расширение (например, "png", "json") — если None, все
keep_last_n — сколько файлов оставить
Пример:

python
1
cleanup_old_files(ext="png", keep_last_n=10)
Автоматическая генерация имён
При filename=None имя файла генерируется по шаблону:

1
{prefix}_{YYYYMMDD_HHMMSS}_{6_random_chars}.{ext}
Пример:

weather_graph_20250405_123456_a1b2c3.png
forecast_data_20250405_123456_x9y8z7.json
Папка data/
Все файлы сохраняются в project_root/data/
Папка создаётся автоматически при первом использовании
Файлы не перезаписываются — создаются новые с уникальным именем
Примеры использования в скриптах
В scripts/weather/weather_graph_script.py:
python
1234567891011
import matplotlib.pyplot as plt
from core.utils.cache_manager import save_plot

def main():
    # ... ваша логика построения графика ...
    fig, ax = plt.subplots()
    ax.plot(times, temps)

    # Сохраняем
    path = save_plot(fig, prefix="weather")

В scripts/meteo/user_profile_script.py:
python
123456
from core.utils.cache_manager import save_json

def main():
    profile_data = {"stress_index": 0.7, "health_risk": "medium", ...}
    path = save_json(profile_data, prefix="user_profile")
    print(f"PROFILE_SAVED:{path}")
Логирование
Все операции логируются в logs/app.log, logs/debug.log.

Пример:

1
2025-04-05 12:34:56 | INFO | cache_manager | save_plot | График сохранён: data/weather_graph_20250405_123456_a1b2c3.png
