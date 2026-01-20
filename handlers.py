from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Order
from keyboards import main_keyboard, order_card_buttons, main_menu, order_type_selection, confirm_order, orders_navigation, back_to_menu, admin_panel
from api_client import api_client
from order_processor import order_processor
from config import settings
from datetime import datetime

router = Router()


# ============ FSM States ============
class OrderCreation(StatesGroup):
    waiting_for_type = State()
    waiting_for_price = State()
    waiting_for_quantity = State()
    confirming = State()


class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_user_id_to_remove = State()


# ============ START & MENU ============
@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user_id = message.from_user.id
    
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user and user_id != settings.OWNER_ID:
        await message.answer(
            "🚫 <b>Доступ заборонено</b>\n\n"
            "Цей бот доступний тільки авторизованим користувачам.",
            parse_mode="HTML"
        )
        return
    
    if not user:
        user = User(id=user_id, username=message.from_user.username, first_name=message.from_user.first_name)
        session.add(user)
        await session.commit()
    
    if user.is_blocked:
        await message.answer("🚫 <b>Доступ заборонено</b>\n\nВаш обліковий запис заблокований.", parse_mode="HTML")
        return
    
    is_owner = user_id == settings.OWNER_ID
    
    await message.answer(
        f"👋 Вітаю, <b>{message.from_user.first_name}</b>!\n\n"
        f"🤖 Це бот для автоматичної торгівлі Gmail акаунтами.\n\n"
        f"Використовуйте кнопки знизу для навігації:",
        reply_markup=main_keyboard(is_owner=is_owner),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    is_owner = callback.from_user.id == settings.OWNER_ID
    await callback.message.edit_text(
        "🏠 <b>Головне меню</b>\n\nОберіть дію:",
        reply_markup=main_menu(is_owner=is_owner),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_prices")
async def show_current_prices(callback: CallbackQuery):
    try:
        prices = await order_processor.get_current_prices()
        text = (
            f"📊 <b>Поточні ціни на акаунти</b>\n\n"
            f"Без 2FA: <b>${prices['no_2fa']:.2f}</b>\n"
            f"З 2FA: <b>${prices['2fa']:.2f}</b>\n\n"
            f"🕐 Оновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        await callback.message.edit_text(text, reply_markup=back_to_menu(), parse_mode="HTML")
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Помилка отримання цін</b>\n\nДеталі: {str(e)}",
            reply_markup=back_to_menu(), parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "show_balance")
async def show_balance(callback: CallbackQuery):
    try:
        balance = await api_client.get_balance()
        text = (
            f"💰 <b>Баланс API</b>\n\n"
            f"Доступно: <b>${balance:.2f}</b>\n\n"
            f"ℹ️ Поповнити баланс можна в дашборді:\n{settings.API_DOMAIN}"
        )
        await callback.message.edit_text(text, reply_markup=back_to_menu(), parse_mode="HTML")
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Помилка отримання балансу</b>\n\nДеталі: {str(e)}",
            reply_markup=back_to_menu(), parse_mode="HTML"
        )
    await callback.answer()


# ============ TEXT BUTTON HANDLERS ============
@router.message(F.text == "📊 Ціни")
async def handle_prices_button(message: Message):
    try:
        prices = await order_processor.get_current_prices()
        text = (
            f"📊 <b>Поточні ціни на акаунти</b>\n\n"
            f"Без 2FA: <b>${prices['no_2fa']:.2f}</b>\n"
            f"З 2FA: <b>${prices['2fa']:.2f}</b>\n\n"
            f"🕐 Оновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ <b>Помилка отримання цін</b>\n\nДеталі: {str(e)}", parse_mode="HTML")


@router.message(F.text == "📝 Ордери")
async def handle_orders_button(message: Message, session: AsyncSession):
    await show_orders_list(message, session)


@router.message(F.text == "➕ Створити")
async def handle_create_button(message: Message, state: FSMContext):
    await state.set_state(OrderCreation.waiting_for_type)
    await message.answer(
        "📝 <b>Створення нового ордера</b>\n\n1️⃣ Оберіть тип акаунтів:",
        reply_markup=order_type_selection(), parse_mode="HTML"
    )


@router.message(F.text == "💰 Баланс")
async def handle_balance_button(message: Message):
    try:
        balance = await api_client.get_balance()
        text = (
            f"💰 <b>Баланс API</b>\n\n"
            f"Доступно: <b>${balance:.2f}</b>\n\n"
            f"ℹ️ Поповнити баланс можна в дашборді:\n{settings.API_DOMAIN}"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ <b>Помилка отримання балансу</b>\n\nДеталі: {str(e)}", parse_mode="HTML")


@router.message(F.text == "⚙️ Адмін")
async def handle_admin_button(message: Message):
    if message.from_user.id != settings.OWNER_ID:
        await message.answer("🚫 У вас немає доступу до адмін-панелі")
        return
    
    await message.answer(
        "⚙️ <b>Панель адміністратора</b>\n\nОберіть дію:",
        reply_markup=admin_panel(), parse_mode="HTML"
    )


# ============ ORDERS ============
@router.callback_query(F.data == "create_order")
async def start_order_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderCreation.waiting_for_type)
    await callback.message.edit_text(
        "📝 <b>Створення нового ордера</b>\n\n1️⃣ Оберіть тип акаунтів:",
        reply_markup=order_type_selection(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_type:"))
async def process_order_type(callback: CallbackQuery, state: FSMContext):
    order_type = callback.data.split(":")[1]
    is_2fa = order_type == "2fa"
    
    await state.update_data(is_2fa=is_2fa)
    await state.set_state(OrderCreation.waiting_for_price)
    
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
            f"❌ Помилка: {str(e)}", reply_markup=back_to_menu(), parse_mode="HTML"
        )
        await state.clear()
    await callback.answer()


@router.message(OrderCreation.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
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
        await message.answer("❌ Невірний формат. Введіть число (наприклад: 0.50):")


@router.message(OrderCreation.waiting_for_quantity)
async def process_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity < 1 or quantity > 3000:
            await message.answer("❌ Кількість повинна бути від 1 до 3000:")
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
            f"ℹ️ Ордер буде виконано автоматично.",
            reply_markup=confirm_order(), parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Невірний формат. Введіть ціле число:")


@router.callback_query(F.data == "confirm_order", OrderCreation.confirming)
async def confirm_order_creation(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    
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
        f"Ціна: <b>${data['target_price']:.2f}</b>\n"
        f"Кількість: <b>{data['quantity']}</b> шт\n\n"
        f"🔔 Ви отримаєте повідомлення про виконання.",
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer("Ордер створено! ✅")


@router.callback_query(F.data == "cancel_order_creation")
async def cancel_order_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Створення скасовано.", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery, session: AsyncSession):
    await _display_orders_inline(callback, session)


@router.callback_query(F.data == "refresh_orders")
async def refresh_orders(callback: CallbackQuery, session: AsyncSession):
    await _display_orders_inline(callback, session)
    await callback.answer("Оновлено ✓")


async def show_orders_list(message: Message, session: AsyncSession):
    """Показати список ордерів через текстову команду"""
    user_id = message.from_user.id
    
    query = select(Order).where(Order.user_id == user_id, Order.status == "active").order_by(Order.created_at.desc())
    result = await session.execute(query)
    orders = result.scalars().all()
    
    if not orders:
        await message.answer("📝 <b>Мої ордери</b>\n\nУ вас немає активних ордерів.", parse_mode="HTML")
        return
    
    try:
        prices = await order_processor.get_current_prices()
    except:
        prices = {'no_2fa': 0, '2fa': 0}
    
    for order in orders:
        type_text = "З 2FA" if order.is_2fa else "Без 2FA"
        current_price = prices['2fa'] if order.is_2fa else prices['no_2fa']
        max_cost = order.target_price * order.quantity
        status_icon = "🟢" if current_price <= order.target_price else "🔴"
        
        text = (
            f"{status_icon} <b>Ордер #{order.id}</b>\n\n"
            f"Тип: <b>{type_text}</b>\n"
            f"Цільова ціна: <b>${order.target_price:.2f}</b>\n"
            f"Кількість: <b>{order.quantity}</b> шт\n"
            f"Макс. сума: <b>${max_cost:.2f}</b>\n\n"
            f"Поточна ціна: <b>${current_price:.2f}</b>\n"
            f"Створено: {order.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await message.answer(text, reply_markup=order_card_buttons(order.id), parse_mode="HTML")


async def _display_orders_inline(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    
    query = select(Order).where(Order.user_id == user_id, Order.status == "active").order_by(Order.created_at.desc())
    result = await session.execute(query)
    orders = result.scalars().all()
    
    if not orders:
        await callback.message.edit_text(
            "📝 <b>Мої ордери</b>\n\nУ вас немає активних ордерів.",
            reply_markup=back_to_menu(), parse_mode="HTML"
        )
        return
    
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
    
    await callback.message.edit_text(text, reply_markup=orders_navigation(), parse_mode="HTML")


@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order_handler(callback: CallbackQuery, session: AsyncSession):
    """Скасувати конкретний ордер"""
    order_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    query = select(Order).where(Order.id == order_id, Order.user_id == user_id)
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        await callback.answer("❌ Ордер не знайдено", show_alert=True)
        return
    
    if order.status != "active":
        await callback.answer("❌ Цей ордер вже неактивний", show_alert=True)
        return
    
    order.status = "cancelled"
    await session.commit()
    
    try:
        await callback.message.edit_text(
            f"❌ <b>Ордер #{order_id} скасовано</b>",
            parse_mode="HTML"
        )
    except:
        pass
    
    await callback.answer("✓ Ордер скасовано", show_alert=True)


# ============ ADMIN ============
@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("Немає доступу", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Панель адміністратора</b>\n\nОберіть дію:",
        reply_markup=admin_panel(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_user")
async def start_add_user(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("Немає доступу", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.message.edit_text(
        "➕ <b>Додавання користувача</b>\n\nВведіть Telegram ID:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id)
async def process_add_user(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != settings.OWNER_ID:
        return
    
    try:
        user_id = int(message.text)
        
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.is_blocked:
                existing_user.is_blocked = False
                await session.commit()
                await message.answer(
                    f"✅ Користувача <code>{user_id}</code> розблоковано!",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"ℹ️ Користувач <code>{user_id}</code> вже має доступ.",
                    parse_mode="HTML"
                )
        else:
            new_user = User(id=user_id)
            session.add(new_user)
            await session.commit()
            
            await message.answer(
                f"✅ Користувача <code>{user_id}</code> додано!",
                parse_mode="HTML"
            )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Невірний формат. Введіть ID:")


@router.callback_query(F.data == "admin_remove_user")
async def start_remove_user(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("Немає доступу", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_user_id_to_remove)
    await callback.message.edit_text(
        "🗑 <b>Видалення користувача</b>\n\nВведіть Telegram ID:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id_to_remove)
async def process_remove_user(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != settings.OWNER_ID:
        return
    
    try:
        user_id = int(message.text)
        
        if user_id == settings.OWNER_ID:
            await message.answer("❌ Не можна видалити власника!", parse_mode="HTML")
            await state.clear()
            return
        
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            await session.delete(user)
            await session.commit()
            await message.answer(
                f"✅ Користувача <code>{user_id}</code> видалено!",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"❌ Користувача не знайдено.",
                parse_mode="HTML"
            )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Невірний формат. Введіть ID:")


@router.callback_query(F.data == "admin_list_users")
async def list_users(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("Немає доступу", show_alert=True)
        return
    
    query = select(User).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()
    
    if not users:
        await callback.message.edit_text(
            "📋 <b>Список користувачів</b>\n\nКористувачів немає.",
            reply_markup=back_to_menu(), parse_mode="HTML"
        )
        return
    
    text = f"📋 <b>Список користувачів ({len(users)})</b>\n\n"
    
    for user in users:
        status = "🚫 Заблокований" if user.is_blocked else "✅ Активний"
        owner_badge = " 👑" if user.id == settings.OWNER_ID else ""
        username_text = f"@{user.username}" if user.username else "—"
        name_text = user.first_name if user.first_name else "—"
        
        text += (
            f"<b>ID:</b> <code>{user.id}</code>{owner_badge}\n"
            f"<b>Ім'я:</b> {name_text}\n"
            f"<b>Username:</b> {username_text}\n"
            f"<b>Статус:</b> {status}\n\n"
        )
    
    await callback.message.edit_text(text, reply_markup=back_to_menu(), parse_mode="HTML")
    await callback.answer()
