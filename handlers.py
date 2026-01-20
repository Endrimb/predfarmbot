from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, Order, Purchase, Account
from keyboards import main_keyboard, order_card_buttons, main_menu, order_type_selection, confirm_order, orders_navigation, back_to_menu, admin_panel
from api_client import api_client
from order_processor import order_processor
from config import settings
from datetime import datetime
from io import BytesIO

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


@router.message(F.text == "📈 Статистика")
async def handle_statistics_button(message: Message, session: AsyncSession):
    """Показати статистику користувача"""
    user_id = message.from_user.id
    
    # Загальна кількість куплених акаунтів
    total_accounts_query = select(sql_func.count(Account.id)).join(Purchase).join(Order).where(Order.user_id == user_id)
    total_accounts_result = await session.execute(total_accounts_query)
    total_accounts = total_accounts_result.scalar() or 0
    
    # Загальна витрачена сума
    total_spent_query = select(sql_func.sum(Purchase.total_price)).join(Order).where(Order.user_id == user_id)
    total_spent_result = await session.execute(total_spent_query)
    total_spent = total_spent_result.scalar() or 0
    
    # Статистика по типам акаунтів
    # Без 2FA
    no_2fa_count_query = select(sql_func.count(Account.id)).join(Purchase).join(Order).where(
        Order.user_id == user_id,
        Purchase.is_2fa == False
    )
    no_2fa_count_result = await session.execute(no_2fa_count_query)
    no_2fa_count = no_2fa_count_result.scalar() or 0
    
    no_2fa_spent_query = select(sql_func.sum(Purchase.total_price)).join(Order).where(
        Order.user_id == user_id,
        Purchase.is_2fa == False
    )
    no_2fa_spent_result = await session.execute(no_2fa_spent_query)
    no_2fa_spent = no_2fa_spent_result.scalar() or 0
    
    # З 2FA
    with_2fa_count_query = select(sql_func.count(Account.id)).join(Purchase).join(Order).where(
        Order.user_id == user_id,
        Purchase.is_2fa == True
    )
    with_2fa_count_result = await session.execute(with_2fa_count_query)
    with_2fa_count = with_2fa_count_result.scalar() or 0
    
    with_2fa_spent_query = select(sql_func.sum(Purchase.total_price)).join(Order).where(
        Order.user_id == user_id,
        Purchase.is_2fa == True
    )
    with_2fa_spent_result = await session.execute(with_2fa_spent_query)
    with_2fa_spent = with_2fa_spent_result.scalar() or 0
    
    # Статистика по ордерах
    completed_orders_query = select(sql_func.count(Order.id)).where(
        Order.user_id == user_id,
        Order.status == "completed"
    )
    completed_orders_result = await session.execute(completed_orders_query)
    completed_orders = completed_orders_result.scalar() or 0
    
    active_orders_query = select(sql_func.count(Order.id)).where(
        Order.user_id == user_id,
        Order.status == "active"
    )
    active_orders_result = await session.execute(active_orders_query)
    active_orders = active_orders_result.scalar() or 0
    
    cancelled_orders_query = select(sql_func.count(Order.id)).where(
        Order.user_id == user_id,
        Order.status == "cancelled"
    )
    cancelled_orders_result = await session.execute(cancelled_orders_query)
    cancelled_orders = cancelled_orders_result.scalar() or 0
    
    # Середня ціна за акаунт
    avg_price = total_spent / total_accounts if total_accounts > 0 else 0
    
    # Формування тексту
    text = "📈 <b>Ваша статистика</b>\n\n"
    
    text += "💰 <b>Загальні дані:</b>\n"
    text += f"• Куплено акаунтів: <b>{total_accounts}</b> шт\n"
    text += f"• Витрачено: <b>${total_spent:.2f}</b>\n"
    text += f"• Середня ціна: <b>${avg_price:.2f}</b>\n\n"
    
    text += "🔐 <b>По типам:</b>\n"
    text += f"• Без 2FA: <b>{no_2fa_count}</b> шт (<b>${no_2fa_spent:.2f}</b>)\n"
    text += f"• З 2FA: <b>{with_2fa_count}</b> шт (<b>${with_2fa_spent:.2f}</b>)\n\n"
    
    text += "📊 <b>Ордери:</b>\n"
    text += f"• Виконано: <b>{completed_orders}</b>\n"
    text += f"• Активних: <b>{active_orders}</b>\n"
    text += f"• Скасовано: <b>{cancelled_orders}</b>"
    
    await message.answer(text, parse_mode="HTML")


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
    
    # Показуємо і активні, і виконані ордери
    query = select(Order).where(
        Order.user_id == user_id,
        Order.status.in_(["active", "completed"])
    ).order_by(Order.created_at.desc())
    result = await session.execute(query)
    orders = result.scalars().all()
    
    if not orders:
        await message.answer("📝 <b>Мої ордери</b>\n\nУ вас немає ордерів.", parse_mode="HTML")
        return
    
    try:
        prices = await order_processor.get_current_prices()
    except:
        prices = {'no_2fa': 0, '2fa': 0}
    
    for order in orders:
        type_text = "З 2FA" if order.is_2fa else "Без 2FA"
        current_price = prices['2fa'] if order.is_2fa else prices['no_2fa']
        max_cost = order.target_price * order.quantity
        
        if order.status == "completed":
            status_icon = "✅"
            status_text = "Виконано"
        else:
            status_icon = "🟢" if current_price <= order.target_price else "🔴"
            status_text = "Активний"
        
        text = (
            f"{status_icon} <b>Ордер #{order.id}</b> - {status_text}\n\n"
            f"Тип: <b>{type_text}</b>\n"
            f"Цільова ціна: <b>${order.target_price:.2f}</b>\n"
            f"Кількість: <b>{order.quantity}</b> шт\n"
            f"Макс. сума: <b>${max_cost:.2f}</b>\n\n"
        )
        
        if order.status == "completed":
            text += f"Виконано: {order.completed_at.strftime('%d.%m.%Y %H:%M')}"
        else:
            text += (
                f"Поточна ціна: <b>${current_price:.2f}</b>\n"
                f"Створено: {order.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
        
        has_accounts = order.status == "completed"
        await message.answer(text, reply_markup=order_card_buttons(order.id, has_accounts), parse_mode="HTML")


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


@router.callback_query(F.data.startswith("download_accounts:"))
async def download_accounts_handler(callback: CallbackQuery, session: AsyncSession):
    """Завантажити акаунти з виконаного ордера"""
    order_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Перевірити чи ордер належить користувачу
    order_query = select(Order).where(Order.id == order_id, Order.user_id == user_id)
    order_result = await session.execute(order_query)
    order = order_result.scalar_one_or_none()
    
    if not order:
        await callback.answer("❌ Ордер не знайдено", show_alert=True)
        return
    
    if order.status != "completed":
        await callback.answer("❌ Ордер ще не виконано", show_alert=True)
        return
    
    # Отримати всі акаунти з цього ордера
    accounts_query = select(Account).join(Purchase).where(Purchase.order_id == order_id)
    accounts_result = await session.execute(accounts_query)
    accounts = accounts_result.scalars().all()
    
    if not accounts:
        await callback.answer("❌ Акаунти не знайдено", show_alert=True)
        return
    
    # Сформувати файл у форматі: email;password;recovery_email;recovery_messages_url
    file_content = ""
    for account in accounts:
        recovery_email = account.recovery_email or ""
        recovery_url = account.recovery_email_messages_url or ""
        file_content += f"{account.email};{account.password};{recovery_email};{recovery_url}\n"
    
    # Створити файл в пам'яті
    file_bytes = file_content.encode('utf-8')
    file = BufferedInputFile(file_bytes, filename=f"order_{order_id}_accounts.txt")
    
    # Відправити файл
    await callback.message.answer_document(
        document=file,
        caption=f"📥 <b>Акаунти з ордера #{order_id}</b>\n\nКількість: {len(accounts)} шт",
        parse_mode="HTML"
    )
    
    await callback.answer("✓ Файл відправлено")


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
