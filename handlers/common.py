# handlers/common.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
        one_time_keyboard=False  # Меню остаётся видимым, пока не удалим
    )
