# tests/test_menu_crawler.py
"""
Ручейковый тест бизнес-логики (без Telegram моков).
Цель: проверить, что после любого действия состояние БД корректно.
"""

import logging
from core.db.central_db import CentralDB
from process_manager import process_manager

# Инициализация
process_manager.initialize_sync()
db = process_manager.central_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

class BusinessLogicCrawler:
    def __init__(self, user_id: int = 123456789):
        self.user_id = user_id
        self.path = []  # путь действий
        self.errors = []

    def reset_user(self):
        """Полная очистка данных пользователя через прямой SQL."""
        try:
            with sqlite3.connect(process_manager.central_db.db_path) as conn:
                # Удаляем все локации пользователя
                conn.execute("DELETE FROM user_locations WHERE user_id = ?", (self.user_id,))
                # Удаляем самого пользователя (если нужно)
                conn.execute("DELETE FROM users WHERE telegram_id = ?", (self.user_id,))
        except Exception as e:
            logging.warning(f"⚠️ Очистка пользователя {self.user_id} вызвала: {e}")
    def log_step(self, action: str, status: str = "ok"):
        """Логирует шаг с отметкой успеха/ошибки."""
        marker = "✅" if status == "ok" else "❌"
        self.path.append(f"{marker} {action}")
        logging.info(f"  {marker} {action}")

    def run_test(self):
        """Основной сценарий."""
        logging.info("🔍 Начинаем ручейковый тест бизнес-логики...")
        self.path = []
        
        # --- Этап 1: чистое состояние ---
        self.reset_user()
        self.log_step("Сброс данных пользователя")

        # --- Этап 2: добавление первой локации (гео) ---
        try:
            db.create_or_get_user(self.user_id)
            db.add_location(
                user_id=self.user_id,
                location_id="geo:55.7558:37.6176",
                display_name="Москва",
                lat=55.7558,
                lon=37.6176,
                is_default=True
            )
            self.log_step("Добавлена гео-локация 'Москва' (по умолчанию)")
        except Exception as e:
            self.log_step(f"Добавление гео-локации → ОШИБКА: {e}", "error")
            self.errors.append(str(e))

        # --- Этап 3: добавление второй локации (текст) ---
        try:
            db.add_location(
                user_id=self.user_id,
                location_id="text:sochi123",
                display_name="Сочи",
                lat=0.0,
                lon=0.0,
                is_default=False
            )
            self.log_step("Добавлена текстовая локация 'Сочи'")
        except Exception as e:
            self.log_step(f"Добавление текстовой локации → ОШИБКА: {e}", "error")
            self.errors.append(str(e))

        # --- Этап 4: назначить 'Сочи' текущей ---
        try:
            success = db.set_default_location(self.user_id, "text:sochi123")
            if success:
                self.log_step("Локация 'Сочи' назначена текущей")
            else:
                self.log_step("Не удалось назначить 'Сочи' текущей", "error")
                self.errors.append("set_default_location вернул False")
        except Exception as e:
            self.log_step(f"Назначение текущей → ОШИБКА: {e}", "error")
            self.errors.append(str(e))

        # --- Этап 5: удаление 'Москва' ---
        try:
            db.remove_location(self.user_id, "geo:55.7558:37.6176")
            self.log_step("Удалена локация 'Москва'")
        except Exception as e:
            self.log_step(f"Удаление 'Москва' → ОШИБКА: {e}", "error")
            self.errors.append(str(e))

        # --- Этап 6: проверка финального состояния ---
        try:
            locations = db.get_user_locations(self.user_id)
            if len(locations) == 1 and locations[0]["display_name"] == "Сочи" and locations[0]["is_default"]:
                self.log_step("Финальное состояние: только 'Сочи' (текущая) — OK")
            else:
                self.log_step("Финальное состояние некорректно", "error")
                self.errors.append(f"Неверное финальное состояние: {locations}")
        except Exception as e:
            self.log_step(f"Проверка финального состояния → ОШИБКА: {e}", "error")
            self.errors.append(str(e))

        # --- Итог ---
        logging.info("\n" + "="*50)
        logging.info("📌 Путь выполнения:")
        for step in self.path:
            logging.info(f"  {step}")
        logging.info("="*50)
        if self.errors:
            logging.error(f"❌ Обнаружено ошибок: {len(self.errors)}")
            for err in self.errors:
                logging.error(f"  - {err}")
        else:
            logging.info("✅ Все проверки пройдены успешно!")

# Запуск
if __name__ == "__main__":
    crawler = BusinessLogicCrawler()
    crawler.run_test()