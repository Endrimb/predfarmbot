from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from bot.keyboards.inline import main_menu, back_to_menu
from bot.services.api_client import api_client
from bot.services.order_processor import order_processor
from config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    """Обробник команди /start"""
    user_id = message.from_user.id
    
    # Перевірити чи користувач існує в БД
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    # Якщо новий користувач і не є власником - заборонити доступ
    if not user and user_id != settings.OWNER_ID:
        await message.answer(
            "🚫 <b>Доступ заборонено</b>\n\n"
            "Цей бот доступний тільки авторизованим користувачам.\n"
            "Зверніться до адміністратора для отримання доступу.",
            parse_mode="HTML"
        )
        return
    
    # Створити користувача якщо не існує
    if not user:
        user = User(
            id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        session.add(user)
        await session.commit()
    
    # Перевірити чи не заблокований
    if user.is_blocked:
        await message.answer(
            "🚫 <b>Доступ заборонено</b>\n\n"
            "Ваш обліковий запис заблокований.",
            parse_mode="HTML"
        )
        return
    
    # Відобразити головне меню
    is_owner = user_id == settings.OWNER_ID
    
    welcome_text = (
        f"👋 Вітаю, <b>{message.from_user.first_name}</b>!\n\n"
        f"🤖 Це бот для автоматичної торгівлі Gmail акаунтами.\n\n"
        f"<b>Основні можливості:</b>\n"
        f"• Створення ордерів на купівлю за вказаною ціною\n"
        f"• Автоматичне виконання при досягненні ціни\n"
        f"• Моніторинг поточних цін\n"
        f"• Перегляд балансу та історії покупок\n\n"
        f"Оберіть дію з меню:"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=main_menu(is_owner=is_owner),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, session: AsyncSession):
    """Показати головне меню"""
    user_id = callback.from_user.id
    is_owner = user_id == settings.OWNER_ID
    
    await callback.message.edit_text(
        "🏠 <b>Головне меню</b>\n\n"
        "Оберіть дію:",
        reply_markup=main_menu(is_owner=is_owner),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_prices")
async def show_current_prices(callback: CallbackQuery):
    """Показати поточні ціни"""
    try:
        prices = await order_processor.get_current_prices()
        
        from datetime import datetime
        text = (
            f"📊 <b>Поточні ціни на акаунти</b>\n\n"
            f"Без 2FA: <b>${prices['no_2fa']:.2f}</b>\n"
            f"З 2FA: <b>${prices['2fa']:.2f}</b>\n\n"
            f"🕐 Оновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Помилка отримання цін</b>\n\n"
            f"Деталі: {str(e)}",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "show_balance")
async def show_balance(callback: CallbackQuery):
    """Показати баланс API"""
    try:
        balance = await api_client.get_balance()
        
        text = (
            f"💰 <b>Баланс API</b>\n\n"
            f"Доступно: <b>${balance:.2f}</b>\n\n"
            f"ℹ️ Поповнити баланс можна в дашборді:\n"
            f"{settings.API_DOMAIN}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Помилка отримання балансу</b>\n\n"
            f"Деталі: {str(e)}",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )
    
    await callback.answer()