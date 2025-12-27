# test_token.py
from config.bot_config import BOT_TOKEN, DEBUG_MODE

print(f"токен: {BOT_TOKEN}")
print(f"DEBUG_MODE: {DEBUG_MODE}")

if BOT_TOKEN:
    print("✅ Токен успешно загружен")
else:
    print("❌ Токен не найден")