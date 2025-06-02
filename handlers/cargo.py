# handlers/cargo.py

from aiogram import types, Dispatcher
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import get_connection
from datetime import datetime

# 1) Определяем состояния для добавления груза
class CargoStates(StatesGroup):
    city_from       = State()
    region_from     = State()
    city_to         = State()
    region_to       = State()
    date_from       = State()
    date_to         = State()
    weight          = State()
    body_type       = State()
    is_local        = State()
    comment         = State()

# 2) Сценарий: команда /add_cargo
async def cmd_add_cargo(message: types.Message, state: FSMContext):
    # Проверяем, что пользователь уже зарегистрирован
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    await message.answer("📦 Начнём добавление груза.\nОткуда (город):")
    await state.set_state(CargoStates.city_from)

# 3) Состояние: город отправления
async def process_city_from(message: types.Message, state: FSMContext):
    await state.update_data(city_from=message.text)
    await message.answer("Регион отправления:")
    await state.set_state(CargoStates.region_from)

# 4) Состояние: регион отправления
async def process_region_from(message: types.Message, state: FSMContext):
    await state.update_data(region_from=message.text)
    await message.answer("Куда (город):")
    await state.set_state(CargoStates.city_to)

# 5) Состояние: город назначения
async def process_city_to(message: types.Message, state: FSMContext):
    await state.update_data(city_to=message.text)
    await message.answer("Регион назначения:")
    await state.set_state(CargoStates.region_to)

# 6) Состояние: регион назначения
async def process_region_to(message: types.Message, state: FSMContext):
    await state.update_data(region_to=message.text)
    await message.answer("Дата отправления (в формате ДД.ММ.ГГГГ):")
    await state.set_state(CargoStates.date_from)

# 7) Состояние: дата отправления
async def process_date_from(message: types.Message, state: FSMContext):
    await state.update_data(date_from=message.text)
    await message.answer("Дата прибытия (в формате ДД.ММ.ГГГГ):")
    await state.set_state(CargoStates.date_to)

# 8) Состояние: дата прибытия
async def process_date_to(message: types.Message, state: FSMContext):
    await state.update_data(date_to=message.text)
    await message.answer("Вес (в тоннах, цифрой):")
    await state.set_state(CargoStates.weight)

# 9) Состояние: вес
async def process_weight(message: types.Message, state: FSMContext):
    # Лучше убедиться, что введено число
    try:
        weight = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введи вес цифрой (например, 12):")
        return

    await state.update_data(weight=weight)
    # Предлагаем ввести тип кузова
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Рефрижератор")],
            [types.KeyboardButton(text="Тент")],
            [types.KeyboardButton(text="Изотерм")],
            [types.KeyboardButton(text="Не важно")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выбери тип кузова:", reply_markup=kb)
    await state.set_state(CargoStates.body_type)

# 10) Состояние: тип кузова
async def process_body_type(message: types.Message, state: FSMContext):
    await state.update_data(body_type=message.text)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Да (внутригородской)")],
            [types.KeyboardButton(text="Нет (междугородний)")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Внутригородской груз?", reply_markup=kb)
    await state.set_state(CargoStates.is_local)

# 11) Состояние: is_local
async def process_is_local(message: types.Message, state: FSMContext):
    text = message.text.lower()
    is_local = 1 if "да" in text else 0
    await state.update_data(is_local=is_local)
    await message.answer("Добавь комментарий (или напиши 'нет'):")
    await state.set_state(CargoStates.comment)

# 12) Состояние: комментарий и сохранение
async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text.lower() != "нет" else ""
    data = await state.get_data()

    # Извлекаем user_id по telegram_id
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Не удалось найти ваш профиль. Сначала зарегистрируйся через /start.")
        conn.close()
        await state.clear()
        return
    user_id = user["id"]

    # Сохраняем запись о грузе в таблицу cargo
    cursor.execute(
        """
        INSERT INTO cargo (
            user_id,
            city_from, region_from,
            city_to, region_to,
            date_from, date_to,
            weight, body_type,
            is_local, comment, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            data["city_from"], data["region_from"],
            data["city_to"], data["region_to"],
            data["date_from"], data["date_to"],
            data["weight"], data["body_type"],
            data["is_local"], comment,
            datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()

    await message.answer("✅ Груз успешно добавлен!", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

# 13) Команда /find_cargo: начать поиск по базовым фильтрам
async def cmd_find_cargo(message: types.Message, state: FSMContext):
    # Проверка регистрации
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    # Запрашиваем город отправления для фильтра
    await message.answer("🔍 Поиск груза.\nВведите город отправления (или 'все' для любого):")
    await state.set_state(CargoStates.city_from)

# 14) После ввода city_from (повторное использование состояния)
async def filter_city_from(message: types.Message, state: FSMContext):
    await state.update_data(filter_city_from=message.text)
    await message.answer("Введите город назначения (или 'все'):")
    # переиспользуем state City_to, но с другой логикой:
    # отметим, что мы сейчас в режиме поиска
    await state.set_state(CargoStates.city_to)

# 15) После ввода city_to
async def filter_city_to(message: types.Message, state: FSMContext):
    await state.update_data(filter_city_to=message.text)
    await message.answer("Введите минимальную дату отправления (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(CargoStates.date_from)

# 16) После ввода даты отправления
async def filter_date_from(message: types.Message, state: FSMContext):
    await state.update_data(filter_date_from=message.text)
    await message.answer("Введите максимальную дату отправления (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(CargoStates.date_to)

# 17) Сохраняем дату_to и показываем результаты
async def filter_date_to(message: types.Message, state: FSMContext):
    data = await state.get_data()
    filter_city_from = data.get("filter_city_from")
    filter_city_to = data.get("filter_city_to")
    filter_date_from = data.get("filter_date_from")
    filter_date_to = message.text

    # Составляем SQL-запрос динамически:
    query = "SELECT c.id, u.name, c.city_from, c.region_from, c.city_to, c.region_to, c.date_from, c.weight, c.body_type FROM cargo c JOIN users u ON c.user_id = u.id WHERE 1=1"
    params = []

    if filter_city_from.lower() != "все":
        query += " AND c.city_from = ?"
        params.append(filter_city_from)
    if filter_city_to.lower() != "все":
        query += " AND c.city_to = ?"
        params.append(filter_city_to)
    if filter_date_from.lower() != "нет":
        query += " AND date(c.date_from, 'start of day') >= date(?, 'start of day')"
        params.append(filter_date_from)
    if filter_date_to.lower() != "нет":
        query += " AND date(c.date_from, 'start of day') <= date(?, 'start of day')"
        params.append(filter_date_to)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("📬 По вашему запросу ничего не найдено.")
    else:
        text = "📋 Найденные грузы:\n\n"
        for r in rows:
            text += (
                f"ID: {r['id']}\n"
                f"Владелец: {r['name']}\n"
                f"{r['city_from']}, {r['region_from']} → {r['city_to']}, {r['region_to']}\n"
                f"Дата: {r['date_from']}\n"
                f"Вес: {r['weight']} т, Кузов: {r['body_type']}\n\n"
            )
        await message.answer(text)

    await state.clear()

# 18) Регистрация хендлеров в этом модуле
def register_cargo_handlers(dp: Dispatcher):
    dp.message.register(cmd_add_cargo, Command(commands=["add_cargo"]))
    dp.message.register(process_city_from, StateFilter(CargoStates.city_from))
    dp.message.register(process_region_from, StateFilter(CargoStates.region_from))
    dp.message.register(process_city_to, StateFilter(CargoStates.city_to))
    dp.message.register(process_region_to, StateFilter(CargoStates.region_to))
    dp.message.register(process_date_from, StateFilter(CargoStates.date_from))
    dp.message.register(process_date_to, StateFilter(CargoStates.date_to))
    dp.message.register(process_weight, StateFilter(CargoStates.weight))
    dp.message.register(process_body_type, StateFilter(CargoStates.body_type))
    dp.message.register(process_is_local, StateFilter(CargoStates.is_local))
    dp.message.register(process_comment, StateFilter(CargoStates.comment))

    dp.message.register(cmd_find_cargo, Command(commands=["find_cargo"]))
    dp.message.register(filter_city_from, StateFilter(CargoStates.city_from))
    dp.message.register(filter_city_to, StateFilter(CargoStates.city_to))
    dp.message.register(filter_date_from, StateFilter(CargoStates.date_from))
    dp.message.register(filter_date_to, StateFilter(CargoStates.date_to))
