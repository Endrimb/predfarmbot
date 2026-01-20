from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from sqlalchemy import select
from database import async_session_maker
from models import User
from order_processor import order_processor
from aiogram import Bot
import logging

logger = logging.getLogger(__name__)


class BotScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
    
    async def check_and_process_orders(self):
        logger.info("Starting order processing...")
        
        async with async_session_maker() as session:
            try:
                executed_orders = await order_processor.process_orders(session)
                
                for order_info in executed_orders:
                    await self._notify_order_executed(order_info)
                
                if executed_orders:
                    logger.info(f"Processed {len(executed_orders)} orders")
                    
            except Exception as e:
                logger.error(f"Error in order processing: {str(e)}")
    
    async def send_price_notifications(self):
        logger.info("Sending price notifications...")
        
        try:
            prices = await order_processor.get_current_prices()
            
            async with async_session_maker() as session:
                query = select(User).where(User.is_blocked == False)
                result = await session.execute(query)
                users = result.scalars().all()
                
                message = (
                    f"📊 <b>Актуальні ціни на акаунти</b>\n\n"
                    f"Без 2FA: <b>${prices['no_2fa']:.2f}</b>\n"
                    f"З 2FA: <b>${prices['2fa']:.2f}</b>\n\n"
                    f"🕐 Оновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                )
                
                for user in users:
                    try:
                        await self.bot.send_message(chat_id=user.id, text=message, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Failed to send to user {user.id}: {str(e)}")
                
                logger.info(f"Sent to {len(users)} users")
                
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
    
    async def _notify_order_executed(self, order_info: dict):
        message = (
            f"✅ <b>Ордер #{order_info['order_id']} виконано!</b>\n\n"
            f"Куплено: <b>{order_info['accounts_count']}</b> акаунтів\n"
            f"Ціна: <b>${order_info['price_paid']:.2f}</b> за шт\n"
            f"Загальна сума: <b>${order_info['total_price']:.2f}</b>\n"
            f"Pack ID: <code>{order_info['pack_id']}</code>\n\n"
            f"Акаунти збережено в системі ✓"
        )
        
        try:
            await self.bot.send_message(chat_id=order_info['user_id'], text=message, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to notify user: {str(e)}")
    
    def start(self, price_check_interval: int = 5, notification_interval: int = 60):
        self.scheduler.add_job(
            self.check_and_process_orders,
            trigger=IntervalTrigger(minutes=price_check_interval),
            id="process_orders"
        )
        
        self.scheduler.add_job(
            self.send_price_notifications,
            trigger=IntervalTrigger(minutes=notification_interval),
            id="price_notifications"
        )
        
        self.scheduler.start()
        logger.info(f"Scheduler started")
    
    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")