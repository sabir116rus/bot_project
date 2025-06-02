# handlers/registration.py

from aiogram import types, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from db import get_connection
from datetime import datetime


# 1) Определяем набор состояний для FSM
class Registration(StatesGroup):
    name = State()
    city = State()
    phone = State()


# 2) Хендлер команды /start
async def cmd_start(message: Message, state: FSMContext):
    # Проверяем, есть ли пользователь в БД
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        # Если уже зарегистрирован — просто приветствуем
        await message.answer(f"Добро пожаловать обратно, {user['name']}!")
    else:
        # Иначе запускаем сценарий регистрации
        await message.answer("Привет! Давай зарегистрируемся. Как тебя зовут?")
        await state.set_state(Registration.name)


# 3) Состояние: ввод имени
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("В каком городе ты находишься?")
    await state.set_state(Registration.city)


# 4) Состояние: ввод города
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)

    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer("Отправь, пожалуйста, свой номер телефона:", reply_markup=markup)
    await state.set_state(Registration.phone)



# 5) Состояние: ввод/отправка телефона
async def process_phone(message: Message, state: FSMContext):
    # Если пришёл контакт, берём его. Иначе — обычный текст.
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    data = await state.get_data()
    name = data.get("name")
    city = data.get("city")
    telegram_id = message.from_user.id
    created_at = datetime.now().isoformat()

    # Сохраняем в БД (с проверкой UNIQUE по telegram_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, name, city, phone, created_at) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, name, city, phone, created_at)
    )
    conn.commit()
    conn.close()

    # Завершаем регистрацию
    await message.answer(
        f"Регистрация завершена! Приятно познакомиться, {name}.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    # Очищаем состояние FSM
    await state.clear()


# 6) Регистрируем все хендлеры внутри функции

def register_user_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(process_name, StateFilter(Registration.name))
    dp.message.register(process_city, StateFilter(Registration.city))
    dp.message.register(
        process_phone,
        lambda m: m.content_type == "contact",
        StateFilter(Registration.phone)
    )
    dp.message.register(process_phone, StateFilter(Registration.phone))  # для текстового ввода
