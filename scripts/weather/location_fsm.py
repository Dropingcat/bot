# scripts/weather/location_fsm.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging
from process_manager import process_manager
import hashlib
from telegram.constants import ParseMode

# Состояние ТОЛЬКО для добавления новой локации
ADD_LOCATION_INPUT = 1

# === ОСНОВНОЕ МЕНЮ (без FSM) ===
async def show_locations_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню локаций. Работает как /locations."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logging.info(f"👤 Пользователь {user_id}: вызвано /locations")
    db = process_manager.central_db
    locations = db.get_user_locations(user_id)

    if not locations:
        text = "🌍 У вас нет сохранённых локаций.\nДобавьте первую:"
        buttons = [
            [InlineKeyboardButton("📍 Через геопозицию", callback_data="add_geo")],
            [InlineKeyboardButton("⌨️ Ввести название", callback_data="add_text")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
        return

    # Формируем меню
    text = "📌 <b>Ваши локации</b>\n\n"
    default_loc = None
    other_locs = []
    for loc in locations:
        if loc["is_default"]:
            default_loc = loc
        else:
            other_locs.append(loc)

    if default_loc:
        name = default_loc["display_name"][:30] + "..." if len(default_loc["display_name"]) > 30 else default_loc["display_name"]
        text += f"📍 <b>Текущая:</b> {name}\n\n"
    else:
        text += "📍 <b>Текущая:</b> не задана\n\n"  # ← Исправлена опечатка: было "<<b>"

    if other_locs:
        text += "🗄️ <b>Другие локации:</b>\n"
        for i, loc in enumerate(other_locs, 1):
            name = loc["display_name"][:25] + "..." if len(loc["display_name"]) > 25 else loc["display_name"]
            text += f"  {i}. {name}\n"
    else:
        text += "🗄️ <b>Другие локации:</b> отсутствуют\n"

    # Кнопки
    buttons = []
    for loc in locations:
        name = loc["display_name"][:20] + "..." if len(loc["display_name"]) > 20 else loc["display_name"]
        if not loc["is_default"]:
            buttons.append([InlineKeyboardButton(f"🔝 Сделать текущей: {name}", callback_data=f"set_default:{loc['location_id']}")])
        buttons.append([InlineKeyboardButton(f"🗑️ Удалить: {name}", callback_data=f"delete:{loc['location_id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить новую", callback_data="add_new")])
    buttons.append([InlineKeyboardButton("🏠 В главное меню", callback_data="nav_main")])
    # ✅ ВСЕГДА используем context.bot.send_message
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )

# === ОБРАБОТКА INLINE-КНОПОК ===
async def handle_location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    data = query.data

    logging.info(f"🖱️ Пользователь {user_id}: нажата кнопка '{data}'")

    db = process_manager.central_db

    if data == "add_new":
        buttons = [
            [InlineKeyboardButton("📍 Через геопозицию", callback_data="add_geo")],
            [InlineKeyboardButton("⌨️ Ввести название", callback_data="add_text")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text="Выберите способ добавления:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data == "add_geo":
        await context.bot.send_message(
            chat_id=chat_id,
            text="Отправьте геопозицию:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📍 Отправить геопозицию", request_location=True)]
            ], resize_keyboard=True, one_time_keyboard=True)
        )
        return

    if data == "add_text":
        await context.bot.send_message(chat_id=chat_id, text="Введите название города:")
        return ADD_LOCATION_INPUT

    if data.startswith("set_default:"):
        loc_id = data.split(":", 1)[1]
        success = db.set_default_location(user_id, loc_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Локация по умолчанию обновлена!" if success else "❌ Не удалось найти локацию."
        )

    elif data.startswith("delete:"):
        loc_id = data.split(":", 1)[1]
        db.remove_location(user_id, loc_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="🗑️ Локация удалена."
        )

    # Обновляем меню
    await show_locations_menu(update, context)

# === FSM ТОЛЬКО ДЛЯ ТЕКСТА ===
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logging.info(f"⌨️ Пользователь {user_id}: введён текст '{user_input}'")
    db = process_manager.central_db
    db.create_or_get_user(user_id)

    hash_id = hashlib.md5(user_input.encode()).hexdigest()[:8]
    location_id = f"text:{hash_id}"
    display_name = user_input[:30]
    existing = db.get_user_locations(user_id)
    is_default = len(existing) == 0
    db.add_location(
        user_id=user_id,
        location_id=location_id,
        display_name=display_name,
        lat=lat,
        lon=lon,
        is_default=is_default  # ← КЛЮЧЕВОЕ ИЗМЕНЕНИЕ
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ «{display_name}» добавлено!"
    )
    await show_locations_menu(update, context)
    return ConversationHandler.END

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Отменено.")
    await show_locations_menu(update, context)
    return ConversationHandler.END

# === ОБРАБОТКА ГЕОПОЗИЦИИ ===
async def handle_location_geo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    loc = update.message.location
    if not loc:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Координаты не получены."
        )
        return

    logging.info(f"📍 Пользователь {user.id}: получена геопозиция {loc.latitude}, {loc.longitude}")

    lat = round(loc.latitude, 4)
    lon = round(loc.longitude, 4)
    location_id = f"geo:{lat}:{lon}"
    display_name = f"{lat}, {lon}"

    db = process_manager.central_db
    db.create_or_get_user(user.id)
    lat = 0.0
    lon = 0.0
    db.add_location(user.id, location_id, display_name, lat, lon, is_default=True)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Локация «{display_name}» добавлена!"
    )
    await show_locations_menu(update, context)