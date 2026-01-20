from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str
    OWNER_ID: int  # Твій Telegram ID
    
    # Gmail Farmer API
    API_DOMAIN: str = "https://trade.gmailfarmer.com"
    API_KEY: str
    
    # Database
    DATABASE_URL: str
    
    # Scheduler
    PRICE_CHECK_INTERVAL_MINUTES: int = 5
    PRICE_NOTIFICATION_INTERVAL_MINUTES: int = 60
    
    def get_db_url(self) -> str:
        """Автоматично виправляє префікс для асинхронної роботи з PostgreSQL"""
        url = self.DATABASE_URL
        if url and url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url and url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Дозволяємо ігнорувати зайві змінні з оточення
        extra = "ignore"

settings = Settings()