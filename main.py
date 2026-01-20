import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from bot.database.db import init_db, async_session_maker
from bot.handlers import start, orders, admin
from bot.scheduler.tasks import BotScheduler

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Дії при запуску бота"""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")
    
    logger.info(f"Bot started. Owner ID: {settings.OWNER_ID}")


async def on_shutdown(bot: Bot):
    """Дії при зупинці бота"""
    logger.info("Bot shutting down...")


async def main():
    """Головна функція запуску бота"""
    # Створити бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Створити диспетчер
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Підключити middleware для сесій БД
    from aiogram.dispatcher.middlewares.base import BaseMiddleware
    from typing import Callable, Dict, Any, Awaitable
    from aiogram.types import TelegramObject
    
    class DatabaseMiddleware(BaseMiddleware):
        async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
        ) -> Any:
            async with async_session_maker() as session:
                data['session'] = session
                return await handler(event, data)
    
    dp.update.middleware(DatabaseMiddleware())
    
    # Зареєструвати роутери
    dp.include_router(start.router)
    dp.include_router(orders.router)
    dp.include_router(admin.router)
    
    # Зареєструвати startup/shutdown хендлери
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запустити планувальник
    scheduler = BotScheduler(bot)
    scheduler.start(
        price_check_interval=settings.PRICE_CHECK_INTERVAL_MINUTES,
        notification_interval=settings.PRICE_NOTIFICATION_INTERVAL_MINUTES
    )
    
    try:
        # Запустити polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Зупинити планувальник
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")