#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматической генерации структуры проекта
для метеорологического Telegram-бота на Windows 10.

Архитектура:
- Единый контекст: process_manager.py
- Блочная структура: каждый модуль — scripts/<domain>/
- FSM через python-telegram-bot ConversationHandler
- Безопасность: санитизация, валидация, экранирование
- Поддержка Windows: пути, логи, Task Scheduler

Запуск: python setup_project_structure.py
"""

import os
from pathlib import Path

# === ОБНОВЛЁННАЯ СТРУКТУРА ===
STRUCTURE = {
    "config": {
        "__files__": ["bot_config.py", "db_config.py", "process_config.py", "logging_config.py"]
    },
    "core": {
        "db": {
            "__files__": [
                "central_db.py",          # пользователи, локации
                "local_db_weather.py",    # кэш погоды
                "local_db_meteo.py",      # метео-влияния
                "local_db_atmosphere.py", # атмосфера
                "local_db_agro.py",       # агропрогноз
                "process_log_db.py"       # логирование задач
            ]
        },
        "models": {
            "__files__": [
                "weather_response.py",    # Pydantic-схемы
                "location.py",            # CanonicalLocation
                "meteo_impact.py",
                "agro_conditions.py"
            ]
        },
        "utils": {
            "__files__": [
                "api_client.py",          # httpx-клиенты
                "coordinate_manager.py",  # LocationResolver
                "error_handler.py",       # централизованная обработка
                "validator.py",           # sanitize_user_input, validate_coords
                "cache_manager.py"        # управление кэшем
            ]
        },
        "monitoring": {
            "__files__": [
                "health_checker.py",
                "performance_monitor.py",
                "anomaly_detector.py"
            ]
        },
        "__files__": []
    },
    "scripts": {
        "weather": {
            "__files__": [
                "weather_handler.py",     # обработчик /weather
                "location_fsm.py",        # FSM для локаций
                "__init__.py"
            ],
            "_services": {
                "__files__": [
                    "weather_fetcher.py",   # получение + кэширование
                    "location_resolver.py"  # геокодинг + нормализация
                ]
            },
            "_io": {
                "__files__": ["__init__.py"],
                "templates": {
                    "__files__": ["current_weather.html.j2", "forecast.html.j2"]
                }
            }
        },
        "meteo": {
            "__files__": ["meteo_handler.py", "__init__.py"],
            "_services": {
                "__files__": ["impact_analyzer.py", "health_predictor.py"]
            },
            "_io": {
                "__files__": ["__init__.py"],
                "templates": {
                    "__files__": ["meteo_report.html.j2"]
                }
            }
        },
        "atmosphere": {
            "__files__": ["atmosphere_handler.py", "__init__.py"],
            "_services": {
                "__files__": ["celestial_calculator.py"]
            },
            "_io": {
                "__files__": ["__init__.py"],
                "templates": {
                    "__files__": ["atmosphere_report.html.j2"]
                }
            }
        },
        "agro": {
            "__files__": ["agro_handler.py", "__init__.py"],
            "_services": {
                "__files__": ["soil_analyzer.py", "growth_predictor.py"]
            },
            "_io": {
                "__files__": ["__init__.py"],
                "templates": {
                    "__files__": ["agro_report.html.j2"]
                }
            }
        },
        "__files__": ["__init__.py"]
    },
    "workers": {
        "__files__": [
            "cleanup_worker.py",        # очистка кэша и логов
            "notification_worker.py"    # оповещения по расписанию
            # data_fetcher_worker убран — данные запрашиваются on-demand
        ]
    },
    "tests": {
        "unit": {"__files__": []},
        "integration": {"__files__": []},
        "stress": {"__files__": []},
        "__files__": ["__init__.py"]
    },
    "__files__": [
        "bot.py",                     # точка входа (python-telegram-bot)
        "process_manager.py",         # глобальный координатор
        "requirements.txt",
        "README.md"
    ]
}

# Папки, которые не являются Python-пакетами
NON_PACKAGE_DIRS = {"logs", "data", "temp", "docs"}

def create_structure(base_path: Path, structure: dict):
    """Рекурсивно создаёт структуру директорий и файлов"""
    for name, content in structure.items():
        if name == "__files__":
            continue

        path = base_path / name
        path.mkdir(exist_ok=True)
        print(f"📁 Создана папка: {path.relative_to(base_path)}")

        # Добавляем __init__.py, если это Python-пакет
        if name not in NON_PACKAGE_DIRS:
            init_file = path / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""Init module."""\n', encoding="utf-8")
                print(f"  📄 Создан: {init_file.relative_to(base_path)}")

        # Рекурсивный вызов для вложенных папок
        if isinstance(content, dict):
            create_structure(path, content)

    # Создание файлов на текущем уровне
    files = structure.get("__files__", [])
    for filename in files:
        file_path = base_path / filename
        if not file_path.exists():
            if filename.endswith(".py"):
                file_path.write_text('"""Module placeholder."""\n', encoding="utf-8")
            elif filename == "requirements.txt":
                # Обновлённый requirements.txt под Windows и python-telegram-bot
                reqs = """# Core
python-telegram-bot[httpx]==20.7
httpx==0.27.0
Jinja2==3.1.4

# Базы данных
aiosqlite==0.19.0

# Утилиты
pydantic==2.8.2
cachetools==5.3.3
python-dotenv==1.0.1

# Логирование
structlog==24.2.0

# Тестирование
pytest==8.3.2
pytest-asyncio==0.23.7
"""
                file_path.write_text(reqs, encoding="utf-8")
            elif filename == "README.md":
                file_path.write_text("# Meteorological Assistant Bot (Windows 10)\n\nSee docs/ for architecture.\n", encoding="utf-8")
            else:
                file_path.write_text("", encoding="utf-8")
            print(f"📄 Создан файл: {file_path.relative_to(base_path)}")

def create_documentation(base_path: Path):
    """Создаёт STRUCTURE.md с обновлённой архитектурой"""
    doc_content = """<!-- Обновлено для Windows 10 и python-telegram-bot -->
# Структура проекта

## Архитектурные принципы
- **Единый контекст**: `process_manager.py` — все зависимости
- **Без глобальных переменных**: только через `process_manager`
- **Безопасность**: санитизация → валидация → экранирование
- **FSM**: через `python-telegram-bot.ConversationHandler`
- **Кэширование**: локальные БД вместо subprocess
- **Windows-ready**: пути с прямым слешем, логи, Task Scheduler

## Поток данных (пример: погода)
1. `/weather` → `weather_handler.py`
2. Получает локацию из `central_db`
3. Вызывает `weather_fetcher.execute(WeatherRequest)`
4. Форматирует через `Jinja2(autoescape=True)`
5. Отправляет в Telegram

"""
    doc_path = base_path / "STRUCTURE.md"
    doc_path.write_text(doc_content, encoding="utf-8")
    print(f"📄 Создана документация: {doc_path.relative_to(base_path)}")

def create_gitignore(base_path: Path):
    """Создаёт .gitignore с учётом Windows и кэша"""
    gitignore_content = """# Logs
logs/
*.log

# Temporary files
temp/
*.tmp

# Data caches
data/*.db
data/*.png
data/*.html

# IDE
.vscode/
.idea/
*.pyc
__pycache__/

# Secrets
.env
config/secrets.py

# Windows
Thumbs.db
"""
    gitignore_path = base_path / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(gitignore_content, encoding="utf-8")
        print(f"📄 Создан .gitignore")

def main():
    project_root = Path.cwd()
    print(f"🚀 Создание обновлённой структуры проекта в: {project_root}")

    # Создаём корневые папки
    for folder in ["logs", "data", "temp", "docs"]:
        folder_path = project_root / folder
        folder_path.mkdir(exist_ok=True)
        print(f"📁 Создана папка: {folder}")

    # Создаём структуру
    create_structure(project_root, STRUCTURE)

    # Дополнительные файлы
    create_documentation(project_root)
    create_gitignore(project_root)

    print("\n✅ Структура проекта обновлена под Windows 10 и блочную архитектуру!")
    print("🔧 Следующие шаги:")
    print("   1. Настройте .env в корне проекта")
    print("   2. Реализуйте process_manager.initialize()")
    print("   3. Запустите через Task Scheduler (см. docs/deployment.md)")

if __name__ == "__main__":
    main()