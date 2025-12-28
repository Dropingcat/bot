"""Module placeholder."""
# config/bot_config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
@dataclass
class BotConfig:
    telegram_token: str
    weather_api_key: str
    geocoding_api_key: str
    log_level: str = "INFO"

    @classmethod
    def load(cls):
        return cls(
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            weather_api_key=os.getenv("OPENWEATHER_API_KEY", ""),
            geocoding_api_key=os.getenv("OPENCAGE_API_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )