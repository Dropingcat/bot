# core/ui/navigation.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_back_button(callback_data: str) -> InlineKeyboardMarkup:
    """Кнопка 'Назад'."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Назад", callback_data=callback_data)]
    ])

def get_main_menu_button() -> InlineKeyboardMarkup:
    """Кнопка 'В главное меню'."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 В главное меню", callback_data="nav_main")]
    ])

def get_back_and_main_buttons(back_data: str) -> InlineKeyboardMarkup:
    """Обе кнопки: Назад + Главное меню."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Назад", callback_data=back_data)],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="nav_main")]
    ])