from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import User
from bot.keyboards.inline import admin_panel, back_to_menu, user_action_buttons
from config import settings

router = Router()


class AdminStates(StatesGroup):
    """Стани для адміністративних дій"""
    waiting_for_user_id = State()
    waiting_for_user_id_to_remove = State()


@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Показати панель адміністратора"""
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("У вас немає доступу до адмін-панелі", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Панель адміністратора</b>\n\n"
        "Оберіть дію:",
        reply_markup=admin_panel(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_user")
async def start_add_user(callback: CallbackQuery, state: FSMContext):
    """Початок додавання користувача"""
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("У вас немає доступу до адмін-панелі", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_user_id)
    
    await callback.message.edit_text(
        "➕ <b>Додавання користувача</b>\n\n"
        "Введіть Telegram ID користувача:\n\n"
        "ℹ️ Щоб отримати ID, користувач може написати боту @userinfobot",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id)
async def process_add_user(message: Message, state: FSMContext, session: AsyncSession):
    """Обробка додавання користувача"""
    if message.from_user.id != settings.OWNER_ID:
        return
    
    try:
        user_id = int(message.text)
        
        # Перевірити чи користувач вже існує
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.is_blocked:
                existing_user.is_blocked = False
                await session.commit()
                await message.answer(
                    f"✅ Користувача <code>{user_id}</code> розблоковано!",
                    reply_markup=back_to_menu(),
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"ℹ️ Користувач <code>{user_id}</code> вже має доступ.",
                    reply_markup=back_to_menu(),
                    parse_mode="HTML"
                )
        else:
            # Створити нового користувача
            new_user = User(
                id=user_id,
                username=None,
                first_name=None,
                is_blocked=False
            )
            session.add(new_user)
            await session.commit()
            
            await message.answer(
                f"✅ Користувача <code>{user_id}</code> додано!\n\n"
                f"Тепер він може використовувати бота.",
                reply_markup=back_to_menu(),
                parse_mode="HTML"
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Невірний формат ID. Введіть числовий ID користувача:"
        )


@router.callback_query(F.data == "admin_remove_user")
async def start_remove_user(callback: CallbackQuery, state: FSMContext):
    """Початок видалення користувача"""
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("У вас немає доступу до адмін-панелі", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_user_id_to_remove)
    
    await callback.message.edit_text(
        "🗑 <b>Видалення користувача</b>\n\n"
        "Введіть Telegram ID користувача для видалення:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id_to_remove)
async def process_remove_user(message: Message, state: FSMContext, session: AsyncSession):
    """Обробка видалення користувача"""
    if message.from_user.id != settings.OWNER_ID:
        return
    
    try:
        user_id = int(message.text)
        
        if user_id == settings.OWNER_ID:
            await message.answer(
                "❌ Не можна видалити власника бота!",
                reply_markup=back_to_menu(),
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Знайти користувача
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                f"❌ Користувача <code>{user_id}</code> не знайдено.",
                reply_markup=back_to_menu(),
                parse_mode="HTML"
            )
        else:
            await session.delete(user)
            await session.commit()
            
            await message.answer(
                f"✅ Користувача <code>{user_id}</code> видалено!",
                reply_markup=back_to_menu(),
                parse_mode="HTML"
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Невірний формат ID. Введіть числовий ID користувача:"
        )


@router.callback_query(F.data == "admin_list_users")
async def list_users(callback: CallbackQuery, session: AsyncSession):
    """Показати список користувачів"""
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("У вас немає доступу до адмін-панелі", show_alert=True)
        return
    
    # Отримати всіх користувачів
    query = select(User).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()
    
    if not users:
        await callback.message.edit_text(
            "📋 <b>Список користувачів</b>\n\n"
            "Користувачів ще немає.",
            reply_markup=back_to_menu(),
            parse_mode="HTML"
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
            f"<b>Статус:</b> {status}\n"
            f"<b>Доданий:</b> {user.created_at.strftime('%d.%m.%Y')}\n\n"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("block_user:"))
async def block_user(callback: CallbackQuery, session: AsyncSession):
    """Заблокувати користувача"""
    if callback.from_user.id != settings.OWNER_ID:
        await callback.answer("У вас немає доступу до адмін-панелі", show_alert=True)
        return
    
    user_id = int(callback.data.split(":")[1])
    
    if user_id == settings.OWNER_ID:
        await callback.answer("Не можна заблокувати власника!", show_alert=True)
        return
    
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        user.is_blocked = True
        await session.commit()
        await callback.answer("Користувача заблоковано ✓", show_alert=True)
    else:
        await callback.answer("Користувача не знайдено", show_alert=True)