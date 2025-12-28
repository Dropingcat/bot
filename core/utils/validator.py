"""Module placeholder."""
# core/utils/validator.py
import html
import re

def sanitize_user_input(text: str) -> str:
    """Санитизация пользовательского ввода."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    text = html.escape(text.strip())
    # Разрешаем только безопасные символы
    text = re.sub(r"[^а-яА-Яa-zA-Z0-9\s,\.\-\(\)]", "", text)
    return text[:100]  # ограничение длины