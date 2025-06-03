# handlers/profile.py

from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from db import get_connection
from .common import get_main_menu

async def show_profile(message: types.Message):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, city, phone, created_at FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    text = (
        f"👤 <b>Ваш профиль:</b>\n"
        f"Имя: {user['name']}\n"
        f"Город: {user['city']}\n"
        f"Телефон: {user['phone']}\n"
        f"Дата регистрации: {user['created_at'][:10]}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu())

def register_profile_handler(dp: Dispatcher):
    dp.message.register(show_profile, lambda m: m.text == "📋 Мой профиль")
