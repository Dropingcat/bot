<!-- Обновлено для Windows 10 и python-telegram-bot -->
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

