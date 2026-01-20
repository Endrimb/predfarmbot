from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_keyboard(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """Постійна клавіатура знизу"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Ціни"),
        KeyboardButton(text="📝 Ордери")
    )
    builder.row(
        KeyboardButton(text="➕ Створити"),
        KeyboardButton(text="💰 Баланс")
    )
    builder.row(
        KeyboardButton(text="📈 Статистика")
    )
    if is_owner:
        builder.row(KeyboardButton(text="⚙️ Адмін"))
    return builder.as_markup(resize_keyboard=True)


def main_menu(is_owner: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Поточні ціни", callback_data="show_prices"))
    builder.row(InlineKeyboardButton(text="📝 Мої ордери", callback_data="my_orders"))
    builder.row(InlineKeyboardButton(text="➕ Створити ордер", callback_data="create_order"))
    builder.row(InlineKeyboardButton(text="💰 Баланс API", callback_data="show_balance"))
    if is_owner:
        builder.row(InlineKeyboardButton(text="⚙️ Адмін", callback_data="admin_panel"))
    return builder.as_markup()


def order_type_selection() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Без 2FA", callback_data="order_type:no2fa"),
        InlineKeyboardButton(text="З 2FA", callback_data="order_type:2fa")
    )
    builder.row(InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order_creation"))
    return builder.as_markup()


def confirm_order() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Створити", callback_data="confirm_order"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order_creation")
    )
    return builder.as_markup()


def order_card_buttons(order_id: int) -> InlineKeyboardMarkup:
    """Кнопки для конкретного ордера"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel_order:{order_id}"))
    return builder.as_markup()


def orders_navigation() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Оновити", callback_data="refresh_orders"))
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()


def admin_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Додати користувача", callback_data="admin_add_user"))
    builder.row(InlineKeyboardButton(text="🗑 Видалити користувача", callback_data="admin_remove_user"))
    builder.row(InlineKeyboardButton(text="📋 Список користувачів", callback_data="admin_list_users"))
    builder.row(InlineKeyboardButton(text="🏠 Головне меню", callback_data="main_menu"))
    return builder.as_markup()
