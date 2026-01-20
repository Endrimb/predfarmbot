import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject

# ВИПРАВЛЕНО: Імпорти без префікса bot.
from config import settings
from db import init_db, async_session_maker 
import start_handler as start 
import orders_handler as orders 
import admin_handler as admin 
from scheduler import BotScheduler

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMiddleware(BaseMiddleware):
    """Middleware для передачі сесії БД у кожен хендлер"""
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data['session'] = session
            return await handler(event, data)

async def on_startup(bot: Bot):
    """Дії при запуску бота"""
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    logger.info(f"Bot started. Owner ID: {settings.OWNER_ID}")

async def on_shutdown(bot: Bot):
    """Дії при зупинці бота"""
    logger.info("Bot shutting down...")

async def main():
    """Головна функція запуску бота"""
    # Створити бота з налаштуваннями з config.py
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Створити диспетчер
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Підключити middleware
    dp.update.middleware(DatabaseMiddleware())
    
    # Зареєструвати роутери
    dp.include_router(start.router)
    dp.include_router(orders.router)
    dp.include_router(admin.router)
    
    # Зареєструвати startup/shutdown хендлери
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запустити планувальник (Scheduler)
    scheduler = BotScheduler(bot)
    scheduler.start(
        price_check_interval=settings.PRICE_CHECK_INTERVAL_MINUTES,
        notification_interval=settings.PRICE_NOTIFICATION_INTERVAL_MINUTES
    )
    
    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")