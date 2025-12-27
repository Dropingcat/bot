<!-- Автоматически сгенерировано setup_project_structure.py -->
# Структура проекта

Проект разделён на логические модули для обеспечения масштабируемости, тестируемости и отсутствия циклических зависимостей.

## Ключевые принципы
- **bot.py** — только ввод/вывод (Telegram)
- **scripts/** — исполняемые модули (запускаются через subprocess)
- **core/** — ядро с shared-логикой
- **workers/** — фоновые задачи
- Все скрипты взаимодействуют через **event_bus** и **stdout/stderr**
- Запрещены обратные импорты в bot.py


├── config/
│   ├── __init__.py
│   ├── bot_config.py
│   ├── db_config.py
│   ├── logging_config.py
│   └── process_config.py
├── core/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── central_db.py
│   │   ├── local_db_agro.py
│   │   ├── local_db_atmosphere.py
│   │   ├── local_db_meteo.py
│   │   ├── local_db_weather.py
│   │   └── process_log_db.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agro_model.py
│   │   ├── health_predictor.py
│   │   └── meteo_model.py
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── anomaly_detector.py
│   │   ├── health_checker.py
│   │   └── performance_monitor.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── api_client.py
│   │   ├── cache_manager.py
│   │   ├── coordinate_manager.py
│   │   ├── data_processor.py
│   │   ├── error_handler.py
│   │   └── validator.py
│   └── __init__.py
├── data/
├── docs/
├── logs/
├── scripts/
│   ├── agro/
│   │   ├── _processes/
│   │   │   ├── __init__.py
│   │   │   ├── growth_predictor.py
│   │   │   ├── harvest_optimizer.py
│   │   │   └── soil_analyzer.py
│   │   ├── __init__.py
│   │   ├── agro_conditions_script.py
│   │   └── plant_monitor_script.py
│   ├── atmosphere/
│   │   ├── _processes/
│   │   │   ├── __init__.py
│   │   │   ├── phase_calculator.py
│   │   │   ├── pollution_analyzer.py
│   │   │   └── transparency_estimator.py
│   │   ├── __init__.py
│   │   ├── light_pollution_script.py
│   │   ├── moon_phase_script.py
│   │   └── sky_transparency_script.py
│   ├── meteo/
│   │   ├── _processes/
│   │   │   ├── __init__.py
│   │   │   ├── alarm_system.py
│   │   │   ├── front_analyzer.py
│   │   │   ├── health_predictor.py
│   │   │   └── stress_calculator.py
│   │   ├── __init__.py
│   │   ├── baric_anomaly_script.py
│   │   ├── front_forecast_script.py
│   │   ├── impact_forecast_script.py
│   │   └── user_profile_script.py
│   ├── settings/
│   │   ├── _processes/
│   │   │   ├── __init__.py
│   │   │   ├── coordinate_validator.py
│   │   │   └── geocoder.py
│   │   ├── __init__.py
│   │   ├── add_location_script.py
│   │   ├── remove_location_script.py
│   │   └── set_default_location_script.py
│   ├── weather/
│   │   ├── _processes/
│   │   │   ├── __init__.py
│   │   │   ├── data_fetcher.py
│   │   │   ├── formatter.py
│   │   │   ├── interpolator.py
│   │   │   └── validator.py
│   │   ├── __init__.py
│   │   ├── baric_map_daily_script.py
│   │   ├── baric_map_weekly_script.py
│   │   ├── weather_forecast_script.py
│   │   ├── weather_graph_script.py
│   │   └── weather_today_script.py
│   └── __init__.py
├── temp/
├── tests/
│   ├── integration/
│   │   └── __init__.py
│   ├── stress/
│   │   └── __init__.py
│   ├── unit/
│   │   └── __init__.py
│   └── __init__.py
├── workers/
│   ├── __init__.py
│   ├── cleanup_worker.py
│   ├── data_fetcher_worker.py
│   ├── health_check_worker.py
│   └── notification_worker.py
├── bot.py
├── process_manager.py
├── README.md
├── requirements.txt
├── setup_project_structure.py
├── дороная карта.txt
└── новый 1.txt