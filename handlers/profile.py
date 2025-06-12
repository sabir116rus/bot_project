"""Handlers showing user profile information."""

from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from db import (
    get_connection,
    get_cargo_by_user,
    get_trucks_by_user,
    update_user_name,
    update_user_city,
    update_user_phone,
    delete_user,
)
from .common import get_main_menu
from utils import format_date_for_display, validate_phone
from states import UserEditStates


async def show_profile(message: types.Message):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, city, phone, created_at FROM users WHERE telegram_id = ?",
        (message.from_user.id,),
    )
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    created_iso = user["created_at"]
    created_formatted = format_date_for_display(created_iso)

    text = (
        f"👤 <b>Ваш профиль:</b>\n"
        f"Имя: {user['name']}\n"
        f"Город: {user['city']}\n"
        f"Телефон: {user['phone']}\n"
        f"Дата регистрации: {created_formatted}\n"
    )

    cargo_rows = get_cargo_by_user(user["id"])
    truck_rows = get_trucks_by_user(user["id"])

    if cargo_rows:
        text += "\n📦 Ваши грузы:\n"
        for r in cargo_rows:
            date_disp = format_date_for_display(r["date_from"])
            text += (
                f"- {r['city_from']} → {r['city_to']}, {date_disp}, "
                f"{r['weight']} т\n"
            )

    if truck_rows:
        text += "\n🚛 Ваши ТС:\n"
        for r in truck_rows:
            date_disp = format_date_for_display(r["date_from"])
            text += f"- {r['city']}, {date_disp}, {r['weight']} т\n"

    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Изменить профиль", callback_data="edit_profile")],
            [types.InlineKeyboardButton(text="Грузы", callback_data="manage_cargo")],
            [types.InlineKeyboardButton(text="ТС", callback_data="manage_truck")],
        ]
    )
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


async def handle_profile_menu(callback: types.CallbackQuery):
    """Show profile editing options."""
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Изменить имя", callback_data="edit_name")],
            [types.InlineKeyboardButton(text="Изменить город", callback_data="edit_city")],
            [types.InlineKeyboardButton(text="Изменить телефон", callback_data="edit_phone")],
            [types.InlineKeyboardButton(text="Удалить", callback_data="del_profile")],
        ]
    )
    await callback.message.answer("Что изменить?", reply_markup=kb)
    await callback.answer()


async def start_edit_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Новое имя:")
    await state.set_state(UserEditStates.name)
    await callback.answer()


async def start_edit_city(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Новый город:")
    await state.set_state(UserEditStates.city)
    await callback.answer()


async def start_edit_phone(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Новый телефон:")
    await state.set_state(UserEditStates.phone)
    await callback.answer()


async def process_new_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        update_user_name(row["id"], message.text.strip())
    await message.answer("Имя обновлено.", reply_markup=get_main_menu())
    await state.clear()


async def process_new_city(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        update_user_city(row["id"], message.text.strip())
    await message.answer("Город обновлён.", reply_markup=get_main_menu())
    await state.clear()


async def process_new_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not validate_phone(phone):
        await message.answer("Введите телефон в формате +79991234567:")
        return
    user_id = message.from_user.id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        update_user_phone(row["id"], phone)
    await message.answer("Телефон обновлён.", reply_markup=get_main_menu())
    await state.clear()


async def handle_delete_profile(callback: types.CallbackQuery):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        delete_user(row["id"])
    await callback.message.answer("Профиль удалён.", reply_markup=get_main_menu())
    await callback.answer()


async def show_manage_cargo(callback: types.CallbackQuery):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    row = cursor.fetchone()
    if not row:
        await callback.answer()
        return
    cargo_rows = get_cargo_by_user(row["id"])
    text = "\n📦 Ваши грузы:\n"
    kb: list[list[types.InlineKeyboardButton]] = []
    for r in cargo_rows:
        date_disp = format_date_for_display(r["date_from"])
        text += (
            f"- ID {r['id']}: {r['city_from']} → {r['city_to']}, {date_disp}, "
            f"{r['weight']} т\n"
        )
        kb.append([
            types.InlineKeyboardButton(text=f"Изменить ID {r['id']}", callback_data=f"edit_cargo:{r['id']}")
        ])
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb) if kb else None
    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


async def show_manage_truck(callback: types.CallbackQuery):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    row = cursor.fetchone()
    if not row:
        await callback.answer()
        return
    truck_rows = get_trucks_by_user(row["id"])
    text = "\n🚛 Ваши ТС:\n"
    kb: list[list[types.InlineKeyboardButton]] = []
    for r in truck_rows:
        date_disp = format_date_for_display(r["date_from"])
        text += f"- ID {r['id']}: {r['city']}, {date_disp}, {r['weight']} т\n"
        kb.append([
            types.InlineKeyboardButton(text=f"Изменить ID {r['id']}", callback_data=f"edit_truck:{r['id']}")
        ])
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb) if kb else None
    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


def register_profile_handler(dp: Dispatcher):
    dp.message.register(show_profile, lambda m: m.text == "📋 Мой профиль")
    dp.callback_query.register(handle_profile_menu, lambda c: c.data == "edit_profile")
    dp.callback_query.register(show_manage_cargo, lambda c: c.data == "manage_cargo")
    dp.callback_query.register(show_manage_truck, lambda c: c.data == "manage_truck")
    dp.callback_query.register(start_edit_name, lambda c: c.data == "edit_name")
    dp.callback_query.register(start_edit_city, lambda c: c.data == "edit_city")
    dp.callback_query.register(start_edit_phone, lambda c: c.data == "edit_phone")
    dp.callback_query.register(handle_delete_profile, lambda c: c.data == "del_profile")
    dp.message.register(process_new_name, StateFilter(UserEditStates.name))
    dp.message.register(process_new_city, StateFilter(UserEditStates.city))
    dp.message.register(process_new_phone, StateFilter(UserEditStates.phone))
