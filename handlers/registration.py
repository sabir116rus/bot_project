# handlers/registration.py

from aiogram import types, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, ContentType

from db import get_connection
from datetime import datetime
from .common import get_main_menu


class Registration(StatesGroup):
    name  = State()
    city  = State()
    phone = State()


async def cmd_start(message: types.Message, state: FSMContext):
    # Проверяем, зарегистрирован ли уже пользователь
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        # Приветствуем возвращённого пользователя
        name = user["name"]
        await message.answer(
            f"Добро пожаловать обратно, {name}!",
            reply_markup=get_main_menu()
        )
        await state.clear()
    else:
        # Начинаем регистрацию
        await message.answer("Привет! Давай зарегистрируемся. Как тебя зовут?")
        await state.set_state(Registration.name)


async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    # Удаляем сообщение с именем и текущую клавиатуру
    await message.delete()
    await message.answer("В каком городе ты находишься?", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.city)


async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await message.delete()

    markup = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Отправь, пожалуйста, свой номер телефона:", reply_markup=markup)
    await state.set_state(Registration.phone)


async def process_phone(message: types.Message, state: FSMContext):
    # Пришёл контакт либо текст
    if message.content_type == ContentType.CONTACT:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()

    # Сохраняем данные
    data = await state.get_data()
    name = data.get("name")
    city = data.get("city")
    telegram_id = message.from_user.id
    created_at = datetime.now().isoformat()

    # Вставляем или игнорируем, если уже есть
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, name, city, phone, created_at) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, name, city, phone, created_at)
    )
    conn.commit()
    conn.close()

    # Удаляем сообщение с телефоном (контакт или текст)
    await message.delete()

    await message.answer(
        f"Регистрация завершена! Приятно познакомиться, {name}.",
        reply_markup=get_main_menu()
    )
    await state.clear()


def register_user_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))

    # Ввод имени
    dp.message.register(process_name, StateFilter(Registration.name))

    # Ввод города
    dp.message.register(process_city, StateFilter(Registration.city))

    # Обработка контакта (content_type == "contact")
    dp.message.register(
        process_phone,
        StateFilter(Registration.phone),
        lambda m: m.content_type == ContentType.CONTACT
    )

    # Если пользователь вводит телефон текстом
    dp.message.register(
        process_phone,
        StateFilter(Registration.phone),
        lambda m: m.content_type == ContentType.TEXT
    )
