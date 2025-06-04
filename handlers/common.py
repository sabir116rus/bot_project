# handlers/common.py


from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.exceptions import TelegramBadRequest

from utils import format_date_for_display
import logging

def get_main_menu() -> ReplyKeyboardMarkup:
    """
    Возвращает ReplyKeyboardMarkup с основными кнопками:
    Добавить груз, Добавить ТС, Найти груз, Найти ТС, Мой профиль.
    """
    buttons = [
        [KeyboardButton(text="➕ Добавить груз")],
        [KeyboardButton(text="➕ Добавить ТС")],
        [KeyboardButton(text="🔍 Найти груз"), KeyboardButton(text="🔍 Найти ТС")],
        [KeyboardButton(text="📋 Мой профиль")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def ask_and_store(
    message: types.Message,
    state: FSMContext,
    text: str,
    next_state: State,
    reply_markup: types.ReplyKeyboardMarkup | None = None
):
    """
    Удаляет сообщение пользователя и удаляет предыдущий бот-вопрос (если он был сохранён в FSMContext),
    отправляет новый вопрос (text) с необязательным reply_markup и сохраняет его message_id.
    Затем переводит FSM в next_state.
    """
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    # Удаляем предыдущий бот-вопрос
    data = await state.get_data()
    prev_bot_msg_id = data.get("last_bot_message_id")
    if prev_bot_msg_id:
        try:
            await message.chat.delete_message(prev_bot_msg_id)
        except Exception:
            pass  # Игнорируем, если уже удалено или нет прав

    # Отправляем новый вопрос
    if reply_markup:
        bot_msg = await message.answer(text, reply_markup=reply_markup)
    else:
        bot_msg = await message.answer(text)

    # Сохраняем ID только что отправленного сообщения бота
    await state.update_data(last_bot_message_id=bot_msg.message_id)

    # Переходим в следующий статус
    await state.set_state(next_state)


async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отмена текущего действия и возврат в главное меню."""
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_menu())


async def cmd_help(message: types.Message):
    """Выводит справочное сообщение со списком команд."""
    text = (
        "Доступные команды:\n"
        "/start - регистрация или главное меню\n"
        "/help - показать эту справку\n"
        "/cancel - отменить текущую операцию"
    )
    await message.answer(text)


def register_common_handlers(dp: Dispatcher):
    """Регистрация общих хендлеров."""
    dp.message.register(cmd_cancel, Command(commands=["cancel"]))
    dp.message.register(cmd_help, Command(commands=["help"]))


async def show_search_results(message: types.Message, rows, page: int = 0, per_page: int = 5):
    """Send paginated search results with optional navigation buttons."""
    total = len(rows)
    if total == 0:
        await message.answer("📬 По вашему запросу ничего не найдено.", reply_markup=get_main_menu())
        return

    start = page * per_page
    end = start + per_page
    page_rows = rows[start:end]

    # Determine row type
    is_cargo = "city_from" in page_rows[0].keys()
    header = "📋 Найденные грузы:\n\n" if is_cargo else "📋 Найденные ТС:\n\n"
    text = header

    for r in page_rows:
        date_disp = format_date_for_display(r["date_from"])
        if is_cargo:
            text += (
                f"ID: {r['id']}\n"
                f"\u0412\u043b\u0430\u0434\u0435\u043b\u0435\u0446: {r['name']}\n"
                f"{r['city_from']}, {r['region_from']} → {r['city_to']}, {r['region_to']}\n"
                f"\u0414\u0430\u0442\u0430 \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f: {date_disp}\n"
                f"\u0412\u0435\u0441: {r['weight']} \u0442, \u041a\u0443\u0437\u043e\u0432: {r['body_type']}\n\n"
            )
        else:
            text += (
                f"ID: {r['id']}\n"
                f"\u0412\u043b\u0430\u0434\u0435\u043b\u0435\u0446: {r['name']}\n"
                f"{r['city']}, {r['region']}\n"
                f"\u0414\u0430\u0442\u0430 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e: {date_disp}\n"
                f"\u0413\u0440\u0443\u0437\u043e\u043f\u043e\u0434\u044a\u0451\u043c\u043d\u043e\u0441\u0442\u044c: {r['weight']} \u0442, \u041a\u0443\u0437\u043e\u0432: {r['body_type']}\n"
                f"\u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: {r['direction']}\n\n"
            )

    markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None
    if total > per_page:
        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton(text="\u041d\u0430\u0437\u0430\u0434", callback_data=f"page:{page-1}"))
        if end < total:
            buttons.append(InlineKeyboardButton(text="\u0412\u043f\u0435\u0440\u0451\u0434", callback_data=f"page:{page+1}"))
        markup = InlineKeyboardMarkup(inline_keyboard=[buttons])

    try:
        await message.answer(text, reply_markup=markup or get_main_menu())
    except UnicodeEncodeError as e:
        logging.exception("Encoding error with text: %r", text)
        await message.answer("Произошла ошибка при выводе текста.")



