# bot.py
import asyncio
import logging
from pathlib import Path
from telegram import Update, Location
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Импорты ядра
from config.bot_config import BOT_TOKEN
from core.process_manager import enqueue_script, init_process_manager
from core.event_bus import subscribe_async
from core.db.central_db import get_user_locations, add_user
from core.utils.error_handler import log_exception
from core.db.central_db import init_db as init_central_db

# Настройка логгера
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище активных задач: user_id → task_id (опционально)
_ACTIVE_TASKS: dict[int, str] = {}

# === ОБРАБОТЧИКИ СОБЫТИЙ ===
async def post_init(application: Application):
    global _BOT_APP
    _BOT_APP = application

    # 🔥 ИНИЦИАЛИЗАЦИЯ БАЗ ДАННЫХ
    init_central_db()  # ← ДОБАВЬ ЭТУ СТРОКУ

    init_process_manager()
    subscribe_async("task_result", on_task_result)
    subscribe_async("task_error", on_task_error)
    logger.info("✅ Бот, БД и process_manager инициализированы")
async def on_task_result(data: dict):
    """Обработчик результата выполнения скрипта."""
    user_id = data.get("user_id")
    if not user_id:
        logger.warning("Получено событие без user_id: %s", data)
        return

    try:
        # Преобразуем user_id в int (Telegram использует int)
        user_id = int(user_id)
    except (ValueError, TypeError):
        logger.error("Некорректный user_id: %s", user_id)
        return

    # Отправляем результат — зависит от RESULT_TYPE
    result_type = data.get("RESULT_TYPE", "text")
    message = data.get("MESSAGE", "Результат готов.")
    file_path = data.get("FILE_PATH")

    # Получаем приложение (Application) через глобальную ссылку (см. main)
    app = globals().get("_BOT_APP")
    if not app:
        logger.error("Нет ссылки на Telegram Application!")
        return

    try:
        if file_path and Path(file_path).exists():
            with open(file_path, "rb") as f:
                await app.bot.send_photo(chat_id=user_id, photo=f, caption=message)
        else:
            await app.bot.send_message(chat_id=user_id, text=message)
        logger.info("✅ Отправлен результат пользователю %s", user_id)
    except Exception as e:
        log_exception(e, f"Ошибка отправки результата пользователю {user_id}")
        await app.bot.send_message(chat_id=user_id, text="❌ Не удалось отправить результат.")

async def on_task_error(data: dict):
    """Обработчик ошибки выполнения скрипта."""
    user_id = data.get("user_id")
    if not user_id:
        return
    try:
        user_id = int(user_id)
        error_msg = data.get("ERROR_MESSAGE", "Произошла ошибка при обработке запроса.")
        app = globals().get("_BOT_APP")
        if app:
            await app.bot.send_message(chat_id=user_id, text=error_msg)
    except Exception as e:
        log_exception(e, "Ошибка в on_task_error")

# === КОМАНДЫ TELEGRAM ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)  # ← БЕЗ await
    await update.message.reply_text(
        f"Привет, {user.first_name}!\n"
        "📍 Отправь геопозицию, чтобы сохранить локацию."
    )
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ✅ УБРАЛИ await
    locations = get_user_locations(user_id)

    if not locations:
        await update.message.reply_text(
            "❌ У вас нет сохранённых локаций. Отправьте геопозицию!"
        )
        return

    # Берём первую локацию (можно улучшить — выбор через кнопки)
    loc = locations[0]
    lat, lon = loc["lat"], loc["lon"]

    try:
        task_id = await enqueue_script(
            "scripts/weather/weather_today_script.py",
            [str(lat), str(lon), str(user_id)]
        )
        _ACTIVE_TASKS[user_id] = task_id
        await update.message.reply_text("⏳ Запрашиваю прогноз погоды...")
        logger.info("Запущен weather_today_script для user=%s, loc=(%s, %s)", user_id, lat, lon)
    except Exception as e:
        log_exception(e, "Ошибка запуска weather_today_script")
        await update.message.reply_text("❌ Не удалось запустить прогноз.")
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location: Location = update.message.location
    lat, lon = location.latitude, location.longitude

    try:
        # Запускаем скрипт добавления локации
        task_id = await enqueue_script(
            "scripts/settings/add_location_script.py",
            [str(user_id), str(lat), str(lon), "📍 Моя локация"]
        )
        await update.message.reply_text("✅ Локация сохранена!")
        logger.info("Добавлена локация для user=%s: (%s, %s)", user_id, lat, lon)
    except Exception as e:
        log_exception(e, "Ошибка добавления локации")
        await update.message.reply_text("❌ Не удалось сохранить локацию.")

# === ЗАПУСК ===

async def post_init(application: Application):
    """Инициализация после старта бота."""
    global _BOT_APP
    _BOT_APP = application
    init_process_manager()
    subscribe_async("task_result", on_task_result)
    subscribe_async("task_error", on_task_error)
    logger.info("✅ Бот и process_manager инициализированы")



async def post_init(application: Application):
    global _BOT_APP
    _BOT_APP = application

    # 🔥 КРИТИЧЕСКИ ВАЖНО: ИНИЦИАЛИЗИРОВАТЬ БД ПЕРВОЙ!
    init_central_db()  # ← ЭТА СТРОКА ДОЛЖНА БЫТЬ!

    init_process_manager()
    subscribe_async("task_result", on_task_result)
    subscribe_async("task_error", on_task_error)
    logger.info("✅ Бот, БД и process_manager инициализированы")
def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    logger.info("🚀 Запуск Telegram-бота...")
    app.run_polling()

if __name__ == "__main__":
    main()