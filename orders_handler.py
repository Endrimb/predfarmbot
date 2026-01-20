from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import Order
from bot.keyboards.inline import (
    order_type_selection, 
    confirm_order, 
    orders_navigation,
    order_list_buttons,
    back_to_menu
)
from bot.services.order_processor import order_processor
from datetime import datetime

router = Router()


class OrderCreation(StatesGroup):
    """Стани для створення ордера"""
    waiting_for_type = State()
    waiting_for_price = State()
    waiting_for_quantity = State()
    confirming = State()


@router.callback_query(F.data == "create_order")
async def start_order_creation(callback: CallbackQuery, state: FSMContext):
    """Початок створення ордера"""
    await state.set_state(OrderCreation.waiting_for_type)
    
    await callback.message.edit_text(
        "📝 <b>Створення нового ордера</b>\n\n"
        "1️⃣ Оберіть тип акаунтів:",
        reply_markup=order_type_selection(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_type:"))
async def process_order_type(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору типу акаунтів"""
    order_type = callback.data.split(":")[1]
    is_2fa = order_type == "2fa"
    
    await state.update_data(is_2fa=is_2fa)
    await state.set_state(OrderCreation.waiting_for_price)
    
    # Отримати поточну ціну
    try:
        prices = await order_processor.get_current_prices()
        current_price = prices['2fa'] if is_2fa else prices['no_2fa']
        
        await state.update_data(current_price=current_price)
        
        type_text = "З 2FA" if is_2fa else "Без 2FA"
        
        await callback.message.edit_text(
            f"📝 <b>Створення нового ордера</b>\n\n"
            f"Тип: <b>{type_text}</b>\n"
            f"Поточна ціна: <b>${current_price:.2f}</b>\n\n"
            f"2️⃣ Введіть цільову ціну в доларах (наприклад: 0.50):",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Помилка отримання поточної ціни: {str(e)}",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )
        await state.clear()
    
    await callback.answer()


@router.message(OrderCreation.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    """Обробка введеної ціни"""
    try:
        price = float(message.text.replace(",", "."))
        
        if price <= 0:
            await message.answer("❌ Ціна повинна бути більше 0. Спробуйте ще раз:")
            return
        
        await state.update_data(target_price=price)
        await state.set_state(OrderCreation.waiting_for_quantity)
        
        data = await state.get_data()
        type_text = "З 2FA" if data['is_2fa'] else "Без 2FA"
        
        await message.answer(
            f"📝 <b>Створення нового ордера</b>\n\n"
            f"Тип: <b>{type_text}</b>\n"
            f"Цільова ціна: <b>${price:.2f}</b>\n"
            f"Поточна ціна: <b>${data['current_price']:.2f}</b>\n\n"
            f"3️⃣ Введіть кількість акаунтів (1-3000):",
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("❌ Невірний формат ціни. Введіть число (наприклад: 0.50):")


@router.message(OrderCreation.waiting_for_quantity)
async def process_quantity(message: Message, state: FSMContext):
    """Обробка введеної кількості"""
    try:
        quantity = int(message.text)
        
        if quantity < 1 or quantity > 3000:
            await message.answer("❌ Кількість повинна бути від 1 до 3000. Спробуйте ще раз:")
            return
        
        await state.update_data(quantity=quantity)
        await state.set_state(OrderCreation.confirming)
        
        data = await state.get_data()
        type_text = "З 2FA" if data['is_2fa'] else "Без 2FA"
        max_cost = data['target_price'] * quantity
        
        await message.answer(
            f"📝 <b>Підтвердження ордера</b>\n\n"
            f"Тип: <b>{type_text}</b>\n"
            f"Цільова ціна: <b>${data['target_price']:.2f}</b>\n"
            f"Поточна ціна: <b>${data['current_price']:.2f}</b>\n"
            f"Кількість: <b>{quantity}</b> шт\n"
            f"Максимальна сума: <b>${max_cost:.2f}</b>\n\n"
            f"ℹ️ Ордер буде виконано автоматично, коли ціна досягне вказаного рівня.",
            reply_markup=confirm_order(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("❌ Невірний формат кількості. Введіть ціле число:")


@router.callback_query(F.data == "confirm_order", OrderCreation.confirming)
async def confirm_order_creation(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Підтвердження створення ордера"""
    data = await state.get_data()
    
    # Створити ордер в БД
    order = Order(
        user_id=callback.from_user.id,
        target_price=data['target_price'],
        quantity=data['quantity'],
        is_2fa=data['is_2fa'],
        status="active"
    )
    
    session.add(order)
    await session.commit()
    await session.refresh(order)
    
    type_text = "З 2FA" if data['is_2fa'] else "Без 2FA"
    
    await callback.message.edit_text(
        f"✅ <b>Ордер #{order.id} створено!</b>\n\n"
        f"Тип: <b>{type_text}</b>\n"
        f"Цільова ціна: <b>${data['target_price']:.2f}</b>\n"
        f"Кількість: <b>{data['quantity']}</b> шт\n"
        f"Створено: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"🔔 Ви отримаєте повідомлення, коли ордер буде виконано.",
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer("Ордер успішно створено! ✅")


@router.callback_query(F.data == "cancel_order_creation")
async def cancel_order_creation(callback: CallbackQuery, state: FSMContext):
    """Скасування створення ордера"""
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Створення ордера скасовано.",
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery, session: AsyncSession):
    """Показати список ордерів користувача"""
    await _display_orders(callback, session)


@router.callback_query(F.data == "refresh_orders")
async def refresh_orders(callback: CallbackQuery, session: AsyncSession):
    """Оновити список ордерів"""
    await _display_orders(callback, session)
    await callback.answer("Список оновлено ✓")


async def _display_orders(callback: CallbackQuery, session: AsyncSession):
    """Відобразити список ордерів"""
    user_id = callback.from_user.id
    
    # Отримати активні ордери
    query = select(Order).where(
        Order.user_id == user_id,
        Order.status == "active"
    ).order_by(Order.created_at.desc())
    
    result = await session.execute(query)
    orders = result.scalars().all()
    
    if not orders:
        await callback.message.edit_text(
            "📝 <b>Мої ордери</b>\n\n"
            "У вас немає активних ордерів.\n\n"
            "Створіть новий ордер через головне меню.",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
        )
        return
    
    # Отримати поточні ціни
    try:
        prices = await order_processor.get_current_prices()
    except:
        prices = {'no_2fa': 0, '2fa': 0}
    
    text = f"📝 <b>Активні ордери ({len(orders)})</b>\n\n"
    
    for order in orders:
        type_text = "З 2FA" if order.is_2fa else "Без 2FA"
        current_price = prices['2fa'] if order.is_2fa else prices['no_2fa']
        max_cost = order.target_price * order.quantity
        
        status_icon = "🟢" if current_price <= order.target_price else "🔴"
        
        text += (
            f"{status_icon} <b>Ордер #{order.id}</b>\n"
            f"Тип: {type_text}\n"
            f"Ціна: ${order.target_price:.2f} × {order.quantity} шт\n"
            f"Макс. сума: ${max_cost:.2f}\n"
            f"Поточна ціна: ${current_price:.2f}\n"
            f"Створено: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=orders_navigation(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order(callback: CallbackQuery, session: AsyncSession):
    """Скасувати ордер"""
    order_id = int(callback.data.split(":")[1])
    
    query = select(Order).where(
        Order.id == order_id,
        Order.user_id == callback.from_user.id
    )
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        await callback.answer("Ордер не знайдено", show_alert=True)
        return
    
    if order.status != "active":
        await callback.answer("Цей ордер вже неактивний", show_alert=True)
        return
    
    order.status = "cancelled"
    await session.commit()
    
    await callback.answer("Ордер скасовано ✓", show_alert=True)
    await _display_orders(callback, session)