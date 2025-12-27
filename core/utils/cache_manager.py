"""Module placeholder."""
# -*- coding: utf-8 -*-
"""
Менеджер кэширования и сохранения файлов.

Сохраняет:
- Графики (matplotlib, PIL)
- JSON-данные
- CSV-данные
- HTML-страницы
- Временные файлы

С именами вида: `{prefix}_{timestamp}_{random_suffix}.{ext}`
"""

import os
import json
import csv
import logging
from pathlib import Path
from datetime import datetime
import hashlib
import random
import string

logger = logging.getLogger("cache_manager")

# === КОНФИГУРАЦИЯ ===
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def generate_unique_filename(prefix: str, ext: str) -> str:
    """
    Генерирует уникальное имя файла.

    Args:
        prefix (str): Префикс (например, "weather_graph", "forecast_data")
        ext (str): Расширение (например, "png", "json")

    Returns:
        str: Уникальное имя файла
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{timestamp}_{random_suffix}.{ext}"

def save_plot(data, filename: str = None, prefix: str = "plot") -> str:
    """
    Сохраняет matplotlib-график или PIL-изображение.

    Args:
        data: matplotlib.figure.Figure или PIL.Image
        filename (str): Имя файла (если None — генерируется автоматически)
        prefix (str): Префикс для автогенерации

    Returns:
        str: Путь к файлу
    """
    if filename is None:
        filename = generate_unique_filename(prefix, "png")

    full_path = DATA_DIR / filename

    if hasattr(data, 'savefig'):  # matplotlib figure
        data.savefig(full_path)
    elif hasattr(data, 'save'):  # PIL image
        data.save(full_path)
    else:
        raise ValueError(f"❌ Неизвестный тип данных для сохранения графика: {type(data)}")

    logger.info(f"💾 График сохранён: {full_path}")
    return str(full_path)

def save_json(data: dict, filename: str = None, prefix: str = "data") -> str:
    """
    Сохраняет словарь как JSON.

    Args:
        data (dict): Данные для сохранения
        filename (str): Имя файла (если None — генерируется автоматически)
        prefix (str): Префикс для автогенерации

    Returns:
        str: Путь к файлу
    """
    if filename is None:
        filename = generate_unique_filename(prefix, "json")

    full_path = DATA_DIR / filename

    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 JSON сохранён: {full_path}")
    return str(full_path)

def save_csv(data: list, headers: list = None, filename: str = None, prefix: str = "data") -> str:
    """
    Сохраняет список списков или список словарей как CSV.

    Args:
        data (list): Данные (например, [[1,2], [3,4]] или [{'a': 1}, {'a': 2}])
        headers (list): Заголовки (если None — генерируются из первой строки)
        filename (str): Имя файла (если None — генерируется автоматически)
        prefix (str): Префикс для автогенерации

    Returns:
        str: Путь к файлу
    """
    if filename is None:
        filename = generate_unique_filename(prefix, "csv")

    full_path = DATA_DIR / filename

    with open(full_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
        writer.writerows(data)

    logger.info(f"💾 CSV сохранён: {full_path}")
    return str(full_path)

def save_html(content: str, filename: str = None, prefix: str = "report") -> str:
    """
    Сохраняет HTML-страницу.

    Args:
        content (str): HTML-контент
        filename (str): Имя файла (если None — генерируется автоматически)
        prefix (str): Префикс для автогенерации

    Returns:
        str: Путь к файлу
    """
    if filename is None:
        filename = generate_unique_filename(prefix, "html")

    full_path = DATA_DIR / filename

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"💾 HTML сохранён: {full_path}")
    return str(full_path)

def load_json(filename: str) -> dict:
    """
    Загружает JSON из data/.

    Args:
        filename (str): Имя файла

    Returns:
        dict: Данные или None
    """
    full_path = DATA_DIR / filename
    if not full_path.exists():
        logger.warning(f"❌ Файл не найден: {full_path}")
        return None

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"📂 JSON загружен: {full_path}")
        return data
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки JSON: {e}")
        return None

def get_recent_files(ext: str = None, limit: int = 10) -> list[str]:
    """
    Возвращает последние файлы из data/ с опциональным расширением.

    Args:
        ext (str): Расширение (например, "png", "json")
        limit (int): Количество файлов

    Returns:
        list[str]: Список имён файлов
    """
    pattern = f"*.{ext}" if ext else "*"
    files = list(DATA_DIR.glob(pattern))
    files.sort(key=os.path.getmtime, reverse=True)
    recent = [f.name for f in files[:limit]]
    logger.info(f"📂 Последние {len(recent)} файлов ({ext or 'все'}): {recent}")
    return recent

def cleanup_old_files(ext: str = None, keep_last_n: int = 20):
    """
    Удаляет старые файлы, оставляя последние N.

    Args:
        ext (str): Расширение (например, "png", "json")
        keep_last_n (int): Сколько файлов оставить
    """
    pattern = f"*.{ext}" if ext else "*"
    files = list(DATA_DIR.glob(pattern))
    files.sort(key=os.path.getmtime)

    to_delete = files[:-keep_last_n] if len(files) > keep_last_n else []
    for f in to_delete:
        f.unlink()
        logger.info(f"🗑️  Удалён старый файл: {f.name}")

    logger.info(f"🧹 Удалено {len(to_delete)} старых файлов ({ext or 'все'})")