from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional

def main_menu(is_owner: bool = False) -> InlineKeyboardMarkup:
    """Головне меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📊 Поточні ціни", callback_data="show_prices"))
    builder.row(InlineKeyboardButton(text="📝 Мої ордери", callback_data="my_orders"))
    builder.row(InlineKeyboardButton(text="➕ Створити ордер", callback_data="create_order"))
    builder.row(InlineKeyboardButton(text="💰 Баланс API", callback_data="show_balance"))
    
    if is_owner:
        builder.row(InlineKeyboardButton(text="⚙️ Адмін", callback_data="admin_panel"))
    
    return builder.as_markup()

def order_type_selection() -> InlineKeyboardMarkup:
    """Вибір типу акаунтів"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="Без 2FA", callback_data="order_type:no2fa"),
        InlineKeyboardButton(text="З 2FA", callback_data="order_type:2fa")
    )
    builder.row(InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order_creation"))
    
    return builder.as_markup()

def confirm_order(order_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Підтвердження створення ордера"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Створити", callback_data="confirm_order"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order_creation")
    )
    
    return builder.as_markup()

def order_list_buttons(order_id: int) -> InlineKeyboardMarkup:
    """Кнопки для конкретного ордера"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel_order:{order_id}"),
        InlineKeyboardButton(text="📊 Деталі", callback_data=f"order_details:{order_id}")
    )
    
    return builder.as_markup()

def orders_navigation() -> InlineKeyboardMarkup:
    """Навігація по списку ордерів"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="🔄 Оновити", callback_data="refresh_orders"))
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    
    return builder.as_markup()

def back_to_menu() -> InlineKeyboardMarkup:
    """Кнопка повернення в меню"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()

def admin_panel() -> InlineKeyboardMarkup:
    """Панель адміністратора"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="➕ Додати користувача", callback_data="admin_add_user"))
    builder.row(InlineKeyboardButton(text="🗑 Видалити користувача", callback_data="admin_remove_user"))
    builder.row(InlineKeyboardButton(text="📋 Список користувачів", callback_data="admin_list_users"))
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    
    return builder.as_markup()

def user_action_buttons(user_id: int) -> InlineKeyboardMarkup:
    """Кнопки дій з користувачем"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокувати", callback_data=f"block_user:{user_id}"),
        InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_user:{user_id}")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_list_users"))
    
    return builder.as_markup()