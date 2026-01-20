import os
from typing import Optional


class Settings:
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    
    # Gmail Farmer API
    API_DOMAIN: str = os.getenv("API_DOMAIN", "https://trade.gmailfarmer.com")
    API_KEY: str = os.getenv("API_KEY", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Scheduler
    PRICE_CHECK_INTERVAL_MINUTES: int = int(os.getenv("PRICE_CHECK_INTERVAL_MINUTES", "5"))
    PRICE_NOTIFICATION_INTERVAL_MINUTES: int = int(os.getenv("PRICE_NOTIFICATION_INTERVAL_MINUTES", "60"))


settings = Settings()