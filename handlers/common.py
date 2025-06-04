# handlers/common.py

from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.exceptions import TelegramBadRequest


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

