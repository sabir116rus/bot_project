# handlers/common.py

from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State


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
    await message.delete()

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
