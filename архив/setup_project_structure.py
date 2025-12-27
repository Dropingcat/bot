#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматической генерации структуры проекта
для метеорологического Telegram-бота с поддержкой
погоды, метео-влияний, атмосферы и агропрогноза.

Запуск: python setup_project_structure.py
"""

import os
from pathlib import Path

# === ОПИСАНИЕ СТРУКТУРЫ ===
STRUCTURE = {
    "config": {
        "__files__": ["bot_config.py", "db_config.py", "process_config.py", "logging_config.py"]
    },
    "core": {
        "db": {
            "__files__": [
                "central_db.py",
                "local_db_weather.py",
                "local_db_meteo.py",
                "local_db_atmosphere.py",
                "local_db_agro.py",
                "process_log_db.py"
            ]
        },
        "models": {
            "__files__": ["meteo_model.py", "agro_model.py", "health_predictor.py"]
        },
        "utils": {
            "__files__": [
                "api_client.py",
                "data_processor.py",
                "coordinate_manager.py",
                "error_handler.py",
                "validator.py",
                "cache_manager.py"
            ]
        },
        "monitoring": {
            "__files__": ["health_checker.py", "performance_monitor.py", "anomaly_detector.py"]
        },
        "__files__": []  # core/__init__.py будет создан автоматически
    },
    "scripts": {
        "weather": {
            "__files__": [
                "weather_today_script.py",
                "weather_forecast_script.py",
                "weather_graph_script.py",
                "baric_map_daily_script.py",
                "baric_map_weekly_script.py",
                "__init__.py"
            ],
            "_processes": {
                "__files__": ["data_fetcher.py", "validator.py", "interpolator.py", "formatter.py"]
            }
        },
        "meteo": {
            "__files__": [
                "user_profile_script.py",
                "impact_forecast_script.py",
                "front_forecast_script.py",
                "baric_anomaly_script.py",
                "__init__.py"
            ],
            "_processes": {
                "__files__": ["front_analyzer.py", "stress_calculator.py", "health_predictor.py", "alarm_system.py"]
            }
        },
        "atmosphere": {
            "__files__": [
                "moon_phase_script.py",
                "sky_transparency_script.py",
                "light_pollution_script.py",
                "__init__.py"
            ],
            "_processes": {
                "__files__": ["phase_calculator.py", "transparency_estimator.py", "pollution_analyzer.py"]
            }
        },
        "agro": {
            "__files__": [
                "agro_conditions_script.py",
                "plant_monitor_script.py",
                "__init__.py"
            ],
            "_processes": {
                "__files__": ["soil_analyzer.py", "growth_predictor.py", "harvest_optimizer.py"]
            }
        },
        "settings": {
            "__files__": [
                "add_location_script.py",
                "remove_location_script.py",
                "set_default_location_script.py",
                "__init__.py"
            ],
            "_processes": {
                "__files__": ["coordinate_validator.py", "geocoder.py"]
            }
        },
        "__files__": ["__init__.py"]
    },
    "workers": {
        "__files__": [
            "data_fetcher_worker.py",
            "notification_worker.py",
            "health_check_worker.py",
            "cleanup_worker.py"
        ]
    },
    "tests": {
        "unit": {"__files__": []},
        "integration": {"__files__": []},
        "stress": {"__files__": []},
        "__files__": ["__init__.py"]
    },
    "__files__": [
        "bot.py",
        "process_manager.py",
        "requirements.txt",
        "README.md"
    ]
}

# Папки, которые не являются Python-пакетами (не требуют __init__.py)
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
                file_path.write_text("# Project dependencies\n", encoding="utf-8")
            elif filename == "README.md":
                file_path.write_text("# Meteorological Assistant Bot\n", encoding="utf-8")
            else:
                file_path.write_text("", encoding="utf-8")
            print(f"📄 Создан файл: {file_path.relative_to(base_path.parent)}")

def create_documentation(base_path: Path):
    """Создаёт сопроводительный файл STRUCTURE.md"""
    doc_content = """<!-- Автоматически сгенерировано setup_project_structure.py -->
# Структура проекта

Проект разделён на логические модули для обеспечения масштабируемости, тестируемости и отсутствия циклических зависимостей.

## Ключевые принципы
- **bot.py** — только ввод/вывод (Telegram)
- **scripts/** — исполняемые модули (запускаются через subprocess)
- **core/** — ядро с shared-логикой
- **workers/** — фоновые задачи
- Все скрипты взаимодействуют через **event_bus** и **stdout/stderr**
- Запрещены обратные импорты в bot.py

"""
    # Рекурсивно добавляем дерево
    def walk_dir(path: Path, prefix=""):
        items = sorted(path.iterdir())
        dirs = [i for i in items if i.is_dir()]
        files = [i for i in items if i.is_file()]
        
        for i, d in enumerate(dirs):
            is_last = (i == len(dirs) - 1 and not files)
            doc_content_list.append(f"{prefix}{'└── ' if is_last else '├── '}{d.name}/")
            walk_dir(d, prefix + ("    " if is_last else "│   "))
        
        for i, f in enumerate(files):
            is_last = (i == len(files) - 1)
            doc_content_list.append(f"{prefix}{'└── ' if is_last else '├── '}{f.name}")

    doc_content_list = [doc_content]
    walk_dir(base_path)
    
    doc_path = base_path / "STRUCTURE.md"
    doc_path.write_text("\n".join(doc_content_list), encoding="utf-8")
    print(f"📄 Создана документация: {doc_path.relative_to(base_path)}")

def create_gitignore(base_path: Path):
    """Создаёт .gitignore"""
    gitignore_content = """# Logs
logs/
*.log

# Temporary files
temp/
*.tmp

# Data caches
data/*.png
data/*.html
data/*.json

# IDE
.vscode/
.idea/
*.pyc
__pycache__/

# Secrets
config/secrets.py
.env
"""
    gitignore_path = base_path / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(gitignore_content, encoding="utf-8")
        print(f"📄 Создан .gitignore")

def main():
    project_root = Path.cwd()
    print(f"🚀 Создание структуры проекта в: {project_root}")
    
    # Создаём корневые папки, не являющиеся пакетами
    for folder in ["logs", "data", "temp", "docs"]:
        folder_path = project_root / folder
        folder_path.mkdir(exist_ok=True)
        print(f"📁 Создана папка: {folder}")
    
    # Создаём структуру Python-пакетов
    create_structure(project_root, STRUCTURE)
    
    # Дополнительные файлы
    create_documentation(project_root)
    create_gitignore(project_root)
    
    print("\n✅ Структура проекта успешно создана!")
    print("🔧 Следующие шаги:")
    print("   1. Заполните config/*.py")
    print("   2. Реализуйте core/event_bus.py")
    print("   3. Напишите process_manager.py")

if __name__ == "__main__":
    main()