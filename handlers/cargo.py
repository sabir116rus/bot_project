# handlers/cargo.py

from aiogram import types, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton
from db import get_connection
from datetime import datetime

# 1) Состояния для добавления (дополнено отдельным классом)
class CargoAddStates(StatesGroup):
    city_from    = State()
    region_from  = State()
    city_to      = State()
    region_to    = State()
    date_from    = State()
    date_to      = State()
    weight       = State()
    body_type    = State()
    is_local     = State()
    comment      = State()

# 2) Состояния для поиска
class CargoSearchStates(StatesGroup):
    city_from    = State()
    city_to      = State()
    date_from    = State()
    date_to      = State()


# Сценарий: /add_cargo
async def cmd_add_cargo(message: types.Message, state: FSMContext):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    await message.answer("📦 Начнём добавление груза.\nОткуда (город):")
    await state.set_state(CargoAddStates.city_from)

# 3) Состояния «добавления»
async def process_city_from(message: types.Message, state: FSMContext):
    await state.update_data(city_from=message.text)
    await message.answer("Регион отправления:")
    await state.set_state(CargoAddStates.region_from)

async def process_region_from(message: types.Message, state: FSMContext):
    await state.update_data(region_from=message.text)
    await message.answer("Куда (город):")
    await state.set_state(CargoAddStates.city_to)

async def process_city_to(message: types.Message, state: FSMContext):
    await state.update_data(city_to=message.text)
    await message.answer("Регион назначения:")
    await state.set_state(CargoAddStates.region_to)

async def process_region_to(message: types.Message, state: FSMContext):
    await state.update_data(region_to=message.text)
    await message.answer("Дата отправления (ДД.ММ.ГГГГ):")
    await state.set_state(CargoAddStates.date_from)

async def process_date_from(message: types.Message, state: FSMContext):
    # Валидируем дату
    try:
        parsed = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ:")
        return
    await state.update_data(date_from=parsed.strftime("%Y-%m-%d"))
    await message.answer("Дата прибытия (ДД.ММ.ГГГГ):")
    await state.set_state(CargoAddStates.date_to)

async def process_date_to(message: types.Message, state: FSMContext):
    # Валидируем дату и сравниваем с date_from
    try:
        parsed_to = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ:")
        return

    data = await state.get_data()
    df = data.get("date_from")
    dt_from = datetime.strptime(df, "%Y-%m-%d") if df else None
    if dt_from and parsed_to < dt_from:
        await message.answer("Дата прибытия не может быть раньше даты отправления. Повторите ввод:")
        return

    await state.update_data(date_to=parsed_to.strftime("%Y-%m-%d"))
    await message.answer("Вес (в тоннах, цифрой):")
    await state.set_state(CargoAddStates.weight)

async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введи вес цифрой (например, 12):")
        return

    await state.update_data(weight=weight)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Рефрижератор")],
            [KeyboardButton(text="Тент")],
            [KeyboardButton(text="Изотерм")],
            [KeyboardButton(text="Не важно")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выбери тип кузова:", reply_markup=kb)
    await state.set_state(CargoAddStates.body_type)

async def process_body_type(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in ("Рефрижератор", "Тент", "Изотерм", "Не важно"):
        await message.answer("Пожалуйста, нажми одну из кнопок: 'Рефрижератор', 'Тент', 'Изотерм' или 'Не важно'.")
        return

    await state.update_data(body_type=text)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Да (внутригородской)")],
            [types.KeyboardButton(text="Нет (междугородний)")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Внутригородской груз?", reply_markup=kb)
    await state.set_state(CargoAddStates.is_local)

async def process_is_local(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    if not ("да" in text or "нет" in text):
        await message.answer("Пожалуйста, нажми одну из кнопок: 'Да (внутригородской)' или 'Нет (междугородний)'.")
        return

    is_local = 1 if "да" in text else 0
    await state.update_data(is_local=is_local)
    await message.answer("Добавь комментарий (или напиши 'нет'):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CargoAddStates.comment)

async def process_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text.strip().lower() != "нет" else ""
    data = await state.get_data()

    # Проверяем, что все поля есть в data
    required_fields = ["city_from", "region_from", "city_to", "region_to", "date_from", "date_to", "weight", "body_type", "is_local"]
    if not all(f in data for f in required_fields):
        await message.answer("Что-то пошло не так. Попробуй команду /add_cargo ещё раз.")
        await state.clear()
        return

    # Извлекаем user_id
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


# 13) Сценарий поиска: /find_cargo
async def cmd_find_cargo(message: types.Message, state: FSMContext):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    await message.answer("🔍 Поиск груза.\nВведите город отправления (или 'все'):")
    await state.set_state(CargoSearchStates.city_from)

async def filter_city_from(message: types.Message, state: FSMContext):
    await state.update_data(filter_city_from=message.text.strip())
    await message.answer("Введите город назначения (или 'все'):")
    await state.set_state(CargoSearchStates.city_to)

async def filter_city_to(message: types.Message, state: FSMContext):
    await state.update_data(filter_city_to=message.text.strip())
    await message.answer("Введите минимальную дату отправления (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(CargoSearchStates.date_from)

async def filter_date_from(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        try:
            parsed = datetime.strptime(message.text, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ или 'нет'.")
            return
        await state.update_data(filter_date_from=parsed)
    else:
        await state.update_data(filter_date_from="нет")

    await message.answer("Введите максимальную дату отправления (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(CargoSearchStates.date_to)

async def filter_date_to(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        try:
            parsed = datetime.strptime(message.text, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ или 'нет'.")
            return
        await state.update_data(filter_date_to=parsed)
    else:
        await state.update_data(filter_date_to="нет")

    data = await state.get_data()
    fc_from = data.get("filter_city_from", "").lower()
    fc_to   = data.get("filter_city_to", "").lower()
    fd_from = data.get("filter_date_from", "")
    fd_to   = data.get("filter_date_to", "")

    # Собираем SQL
    query = """
    SELECT c.id, u.name, c.city_from, c.region_from, c.city_to, c.region_to, c.date_from, c.weight, c.body_type
    FROM cargo c
    JOIN users u ON c.user_id = u.id
    WHERE 1=1
    """
    params = []
    if fc_from != "все":
        query += " AND lower(c.city_from) = ?"
        params.append(fc_from)
    if fc_to != "все":
        query += " AND lower(c.city_to) = ?"
        params.append(fc_to)
    if fd_from != "нет":
        query += " AND date(c.date_from) >= date(?)"
        params.append(fd_from)
    if fd_to != "нет":
        query += " AND date(c.date_from) <= date(?)"
        params.append(fd_to)

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


# 18) Регистрация хендлеров
def register_cargo_handlers(dp: Dispatcher):
    # Добавление груза
    dp.message.register(cmd_add_cargo, Command(commands=["add_cargo"]))
    dp.message.register(process_city_from,   StateFilter(CargoAddStates.city_from))
    dp.message.register(process_region_from, StateFilter(CargoAddStates.region_from))
    dp.message.register(process_city_to,     StateFilter(CargoAddStates.city_to))
    dp.message.register(process_region_to,   StateFilter(CargoAddStates.region_to))
    dp.message.register(process_date_from,   StateFilter(CargoAddStates.date_from))
    dp.message.register(process_date_to,     StateFilter(CargoAddStates.date_to))
    dp.message.register(process_weight,      StateFilter(CargoAddStates.weight))
    dp.message.register(process_body_type,   StateFilter(CargoAddStates.body_type))
    dp.message.register(process_is_local,    StateFilter(CargoAddStates.is_local))
    dp.message.register(process_comment,     StateFilter(CargoAddStates.comment))

    # Поиск груза
    dp.message.register(cmd_find_cargo,      Command(commands=["find_cargo"]))
    dp.message.register(filter_city_from,    StateFilter(CargoSearchStates.city_from))
    dp.message.register(filter_city_to,      StateFilter(CargoSearchStates.city_to))
    dp.message.register(filter_date_from,    StateFilter(CargoSearchStates.date_from))
    dp.message.register(filter_date_to,      StateFilter(CargoSearchStates.date_to))
