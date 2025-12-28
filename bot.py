# bot.py
# -*- coding: utf-8 -*-
"""
Основной скрипт бота с обновлённым интерфейсом управления локациями.
"""
import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode  # ← ДОБАВЬТЕ ЭТУ СТРОКУ
from process_manager import process_manager

# Импорт обработчиков локаций
from scripts.weather.location_fsm import (
    show_locations_menu,
    handle_location_callback,
    handle_text_input,
    cancel_add,
    ADD_LOCATION_INPUT,
    handle_location_geo
)
from scripts.weather.weather_handler import (
    weather_menu,
    weather_callback,
    weather_back_callback
)
# === Обработчики команд ===
async def global_navigation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка глобальных навигационных кнопок."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "nav_main":
        await start(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🌤️ <b>Метео-бот</b>\n\n"
            "Выберите действие:\n"
            "• /weather — прогноз погоды\n"
            "• /locations — управление локациями"
        ),
        parse_mode=ParseMode.HTML
    )
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"⚠️ Исключение при обработке: {context.error}", exc_info=True)
    if update and hasattr(update, 'update_id'):
        logging.error(f"Update ID: {update.update_id}")
    # Можно отправить сообщение админу
# === Основная функция запуска ===
def main():
    # Инициализация
    process_manager.initialize_sync()
    logging.info("🚀 Запуск бота")
    if not process_manager.config.telegram_token:
        logging.critical("❌ TELEGRAM_BOT_TOKEN не задан")
        raise ValueError(" TELEGRAM_BOT_TOKEN не задан в .env!")

    # Создание приложения
    app = Application.builder().token(process_manager.config.telegram_token).build()

    # === Регистрация обработчиков ===
    app.add_handler(CommandHandler("start", start))

    # Основное меню локаций — обычный CommandHandler
    app.add_handler(CommandHandler("locations", show_locations_menu))

    # FSM только для текстового ввода (запускается через inline-кнопку "add_text")
    add_text_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_location_callback, pattern="^add_text$")
        ],
        states={
            ADD_LOCATION_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_add)
        ],
        per_user=True,
        allow_reentry=True
    )
    app.add_handler(add_text_conv)

    # Обработка ВСЕХ inline-кнопок (включая add_geo, set_default, delete, add_new)
    app.add_handler(CallbackQueryHandler(handle_location_callback))
    #app.add_handler(MessageHandler(filters.LOCATION, handle_location_geo))
    app.add_error_handler(error_handler)
    app.add_handler(MessageHandler(filters.LOCATION, handle_location_geo))
    app.add_handler(CallbackQueryHandler(global_navigation_handler, pattern="^nav_main$"))
    app.add_handler(CommandHandler("weather", weather_menu))
    app.add_handler(CallbackQueryHandler(weather_callback, pattern="^weather_loc:"))
    app.add_handler(CallbackQueryHandler(weather_back_callback, pattern="^weather_back$"))
    
    # === Запуск ===
    print("🚀 Бот запущен. Используйте /locations.")
    print("Нажмите Ctrl+C для остановки.")

    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\n🛑 Остановка по запросу пользователя.")
    finally:
        process_manager.shutdown_sync()
        print("✅ Бот завершил работу.")


if __name__ == "__main__":  # ← Без пробела: `__name__`
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    main()