from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str
    OWNER_ID: int  # Твій Telegram ID
    
    # Gmail Farmer API
    API_DOMAIN: str = "https://trade.gmailfarmer.com"
    API_KEY: str
    
    # Database
    DATABASE_URL: str  # postgresql+asyncpg://user:password@host:port/dbname
    
    # Scheduler
    PRICE_CHECK_INTERVAL_MINUTES: int = 5  # Перевірка цін кожні 5 хвилин
    PRICE_NOTIFICATION_INTERVAL_MINUTES: int = 60  # Сповіщення кожну годину
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()