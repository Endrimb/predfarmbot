import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import TelegramObject

from structure_config import settings
from database import init_db, async_session_maker
from handlers import router
from scheduler import BotScheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


async def main():
    logger.info("Starting bot...")
    
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.update.middleware(DatabaseMiddleware())
    
    dp.include_router(router)
    
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    
    scheduler = BotScheduler(bot)
    scheduler.start(
        price_check_interval=settings.PRICE_CHECK_INTERVAL_MINUTES,
        notification_interval=settings.PRICE_NOTIFICATION_INTERVAL_MINUTES
    )
    
    logger.info(f"Bot started. Owner ID: {settings.OWNER_ID}")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
