"""Handlers for admin functionality."""

from aiogram import Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import Config
from db import get_connection
from metrics import get_bot_statistics
from .common import get_main_menu
from utils import format_date_for_display


def is_admin(user_id: int) -> bool:
    """Return ``True`` if ``user_id`` is in :data:`Config.ADMIN_IDS`."""

    return user_id in Config.ADMIN_IDS


def get_admin_menu() -> types.ReplyKeyboardMarkup:
    """Return keyboard with available admin actions."""

    buttons = [
        [types.KeyboardButton(text="Статистика")],
        [types.KeyboardButton(text="Пользователи")],
        [types.KeyboardButton(text="Активные грузы")],
        [types.KeyboardButton(text="Активные ТС")],
        [types.KeyboardButton(text="Рассылка")],
        [types.KeyboardButton(text="↩️ Выход")],
    ]
    return types.ReplyKeyboardMarkup(
        keyboard=buttons, resize_keyboard=True, one_time_keyboard=False
    )


class AdminStates(StatesGroup):
    broadcast = State()


async def cmd_admin(message: types.Message, state: FSMContext) -> None:
    """Show admin menu if the user has rights."""

    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для входа в админку.")
        return

    await state.clear()
    await message.answer("Админ меню:", reply_markup=get_admin_menu())


async def show_statistics(message: types.Message) -> None:
    """Send bot usage statistics to the admin."""

    if not is_admin(message.from_user.id):
        return

    total, new = get_bot_statistics()
    text = (
        f"Всего пользователей: {total}\n"
        f"Зарегистрировано за 24ч: {new}"
    )
    await message.answer(text)


async def list_users(message: types.Message) -> None:
    """Send a simple list of the latest users."""

    if not is_admin(message.from_user.id):
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT name, city, phone, created_at FROM users ORDER BY created_at DESC LIMIT 20"
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.answer("Пользователи не найдены.")
        return

    lines = ["Пользователи:\n"]
    for r in rows:
        created = format_date_for_display(r["created_at"])
        lines.append(
            f"{r['name']} ({r['city']}, {r['phone']}) — {created}"
        )
    await message.answer("\n".join(lines))


async def list_cargo(message: types.Message) -> None:
    """Show latest cargo entries."""

    if not is_admin(message.from_user.id):
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, city_from, city_to, date_from, weight FROM cargo ORDER BY created_at DESC LIMIT 10"
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.answer("Активных грузов нет.")
        return

    text = "Активные грузы:\n\n"
    for r in rows:
        date_disp = format_date_for_display(r["date_from"])
        text += (
            f"ID {r['id']}: {r['city_from']} → {r['city_to']}, "
            f"{date_disp}, {r['weight']} т\n"
        )

    await message.answer(text)


async def list_trucks(message: types.Message) -> None:
    """Show latest trucks."""

    if not is_admin(message.from_user.id):
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, city, date_from, weight FROM trucks ORDER BY created_at DESC LIMIT 10"
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await message.answer("Активных ТС нет.")
        return

    text = "Активные ТС:\n\n"
    for r in rows:
        date_disp = format_date_for_display(r["date_from"])
        text += (
            f"ID {r['id']}: {r['city']}, {date_disp}, {r['weight']} т\n"
        )

    await message.answer(text)


async def start_broadcast(message: types.Message, state: FSMContext) -> None:
    """Ask admin for broadcast text."""

    if not is_admin(message.from_user.id):
        return

    await state.set_state(AdminStates.broadcast)
    await message.answer("Введите текст рассылки:")


async def process_broadcast(message: types.Message, state: FSMContext) -> None:
    """Send broadcast message to all users."""

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    text = message.text
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT telegram_id FROM users")
    rows = cur.fetchall()
    conn.close()

    for r in rows:
        try:
            await message.bot.send_message(r["telegram_id"], text)
        except Exception:
            pass

    await state.clear()
    await message.answer("Рассылка завершена.", reply_markup=get_admin_menu())


async def exit_admin(message: types.Message, state: FSMContext) -> None:
    """Return to the main menu."""

    await state.clear()
    await message.answer("Выход из админки", reply_markup=get_main_menu())


def register_admin_handlers(dp: Dispatcher) -> None:
    """Register admin command handlers."""

    dp.message.register(cmd_admin, Command(commands=["admin"]))
    dp.message.register(process_broadcast, StateFilter(AdminStates.broadcast))
    dp.message.register(show_statistics, lambda m: m.text == "Статистика")
    dp.message.register(list_users, lambda m: m.text == "Пользователи")
    dp.message.register(list_cargo, lambda m: m.text == "Активные грузы")
    dp.message.register(list_trucks, lambda m: m.text == "Активные ТС")
    dp.message.register(start_broadcast, lambda m: m.text == "Рассылка")
    dp.message.register(exit_admin, lambda m: m.text == "↩️ Выход")
