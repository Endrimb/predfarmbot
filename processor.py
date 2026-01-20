from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models import Order, Purchase, Account, PriceHistory
from bot.services.api_client import api_client
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class OrderProcessor:
    """Обробник ордерів на купівлю акаунтів"""
    
    async def process_orders(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """
        Обробити всі активні ордери.
        Повертає список виконаних ордерів з інформацією про покупку.
        """
        executed_orders = []
        
        try:
            # Отримати поточні ціни
            price_no_2fa = await api_client.get_price(is_2fa=False)
            price_2fa = await api_client.get_price(is_2fa=True)
            
            # Зберегти в історію цін
            await self._save_price_history(session, price_no_2fa, price_2fa)
            
            # Отримати баланс
            balance = await api_client.get_balance()
            
            # Отримати активні ордери, відсортовані по ціні (найдешевші першими)
            query = select(Order).where(
                Order.status == "active"
            ).order_by(Order.target_price.asc())
            
            result = await session.execute(query)
            active_orders = result.scalars().all()
            
            logger.info(f"Processing {len(active_orders)} active orders. Balance: ${balance}")
            
            # Обробити кожен ордер
            for order in active_orders:
                current_price = price_2fa if order.is_2fa else price_no_2fa
                
                # Перевірити чи ціна підходить
                if current_price > order.target_price:
                    continue
                
                # Перевірити чи вистачає балансу
                estimated_cost = current_price * order.quantity
                if balance < estimated_cost:
                    logger.info(f"Order {order.id}: Insufficient balance (need ${estimated_cost}, have ${balance})")
                    continue
                
                # Виконати покупку
                try:
                    purchase_result = await self._execute_purchase(session, order, current_price)
                    if purchase_result:
                        executed_orders.append(purchase_result)
                        balance -= purchase_result['total_price']
                        logger.info(f"Order {order.id}: Successfully executed. Remaining balance: ${balance}")
                
                except Exception as e:
                    logger.error(f"Order {order.id}: Failed to execute - {str(e)}")
                    continue
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error processing orders: {str(e)}")
            await session.rollback()
        
        return executed_orders
    
    async def _execute_purchase(self, session: AsyncSession, order: Order, current_price: float) -> Dict[str, Any]:
        """Виконати покупку для конкретного ордера"""
        try:
            # Купити акаунти через API
            purchase_data = await api_client.buy_accounts(count=order.quantity, is_2fa=order.is_2fa)
            
            # Створити запис про покупку
            purchase = Purchase(
                order_id=order.id,
                pack_id=purchase_data['packId'],
                accounts_count=purchase_data['accountsCount'],
                price_paid=purchase_data['usdPrice'],
                total_price=purchase_data['totalUsdPrice'],
                is_2fa=purchase_data['is2fa']
            )
            session.add(purchase)
            await session.flush()
            
            # Зберегти акаунти
            for account_data in purchase_data.get('accounts', []):
                account = Account(
                    purchase_id=purchase.id,
                    email=account_data['email'],
                    password=account_data['password'],
                    recovery_email=account_data.get('recoveryEmail'),
                    recovery_email_messages_url=account_data.get('recoveryEmailMessagesUrl'),
                    authenticator_token_2fa=account_data.get('authenticatorToken2FA'),
                    app_password=account_data.get('appPassword'),
                    messages_url=account_data.get('messagesUrl')
                )
                session.add(account)
            
            # Оновити статус ордера
            order.status = "completed"
            order.completed_at = datetime.utcnow()
            
            return {
                'order_id': order.id,
                'user_id': order.user_id,
                'pack_id': purchase.pack_id,
                'accounts_count': purchase.accounts_count,
                'price_paid': purchase.price_paid,
                'total_price': purchase.total_price,
                'is_2fa': purchase.is_2fa
            }
            
        except Exception as e:
            logger.error(f"Failed to execute purchase for order {order.id}: {str(e)}")
            raise
    
    async def _save_price_history(self, session: AsyncSession, price_no_2fa: float, price_2fa: float):
        """Зберегти ціни в історію"""
        price_record = PriceHistory(
            price_no_2fa=price_no_2fa,
            price_2fa=price_2fa
        )
        session.add(price_record)
        await session.flush()
    
    async def get_current_prices(self) -> Dict[str, float]:
        """Отримати поточні ціни"""
        price_no_2fa = await api_client.get_price(is_2fa=False)
        price_2fa = await api_client.get_price(is_2fa=True)
        
        return {
            'no_2fa': price_no_2fa,
            '2fa': price_2fa
        }


# Глобальний екземпляр процесора
order_processor = OrderProcessor()