# handlers/truck.py

from aiogram import types, Dispatcher
from aiogram.types import KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import get_connection
from datetime import datetime

class TruckAddStates(StatesGroup):
    city          = State()
    region        = State()
    date_from     = State()
    date_to       = State()
    weight        = State()
    body_type     = State()
    direction     = State()
    route_regions = State()
    comment       = State()

class TruckSearchStates(StatesGroup):
    city          = State()
    date_from     = State()
    date_to       = State()

async def cmd_add_truck(message: types.Message, state: FSMContext):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    await message.answer("🚛 Начнём добавление ТС.\nВ каком городе стоит ТС?")
    await state.set_state(TruckAddStates.city)

async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Регион стоянки:")
    await state.set_state(TruckAddStates.region)

async def process_region(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text)
    await message.answer("Дата доступности (с) (ДД.ММ.ГГГГ):")
    await state.set_state(TruckAddStates.date_from)

async def process_date_from(message: types.Message, state: FSMContext):
    try:
        parsed = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ:")
        return
    await state.update_data(date_from=parsed.strftime("%Y-%m-%d"))
    await message.answer("Дата доступности (по) (ДД.ММ.ГГГГ):")
    await state.set_state(TruckAddStates.date_to)

async def process_date_to(message: types.Message, state: FSMContext):
    try:
        parsed_to = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите ДД.ММ.ГГГГ:")
        return

    data = await state.get_data()
    df = data.get("date_from")
    dt_from = datetime.strptime(df, "%Y-%m-%d") if df else None
    if dt_from and parsed_to < dt_from:
        await message.answer("Дата «по» не может быть раньше даты «с». Повторите ввод:")
        return

    await state.update_data(date_to=parsed_to.strftime("%Y-%m-%d"))
    await message.answer("Грузоподъёмность (в тоннах):")
    await state.set_state(TruckAddStates.weight)

async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = int(message.text)
    except ValueError:
        await message.answer("Введи грузоподъёмность цифрой (например, 15):")
        return

    await state.update_data(weight=weight)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Рефрижератор")],
            [KeyboardButton(text="Тент")],
            [KeyboardButton(text="Изотерм")],
            [KeyboardButton(text="Любой")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выбери тип кузова ТС:", reply_markup=kb)
    await state.set_state(TruckAddStates.body_type)

async def process_body_type(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in ("Рефрижератор", "Тент", "Изотерм", "Любой"):
        await message.answer("Пожалуйста, нажми одну из кнопок: 'Рефрижератор', 'Тент', 'Изотерм' или 'Любой'.")
        return

    await state.update_data(body_type=text)

    # Заменили Inline на ReplyKeyboard
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ищу заказ")],
            [KeyboardButton(text="Попутный путь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выбери направление:", reply_markup=kb)
    await state.set_state(TruckAddStates.direction)

async def process_direction(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in ("Ищу заказ", "Попутный путь"):
        await message.answer("Пожалуйста, нажми «Ищу заказ» или «Попутный путь».")
        return

    await state.update_data(direction=text)
    await message.answer("Перечисли через запятую регионы, где готов ехать (или 'нет'):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(TruckAddStates.route_regions)

async def process_route_regions(message: types.Message, state: FSMContext):
    regions_input = message.text
    regions = regions_input if regions_input.strip().lower() != "нет" else ""
    await state.update_data(route_regions=regions)
    await message.answer("Добавь комментарий (или напиши 'нет'):")
    await state.set_state(TruckAddStates.comment)

async def process_truck_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text.strip().lower() != "нет" else ""
    data = await state.get_data()

    required = ["city", "region", "date_from", "date_to", "weight", "body_type", "direction", "route_regions"]
    if not all(k in data for k in required):
        await message.answer("Что-то пошло не так. Попробуй /add_truck ещё раз.")
        await state.clear()
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("Не удалось найти профиль. Сначала /start.")
        conn.close()
        await state.clear()
        return

    user_id = user["id"]
    cursor.execute(
        """
        INSERT INTO trucks (
            user_id, city, region,
            date_from, date_to,
            weight, body_type,
            direction, route_regions,
            comment, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            data["city"], data["region"],
            data["date_from"], data["date_to"],
            data["weight"], data["body_type"],
            data["direction"], data["route_regions"],
            comment, datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()

    await message.answer("✅ ТС успешно добавлено!", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


async def cmd_find_trucks(message: types.Message, state: FSMContext):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    await message.answer("🔍 Поиск ТС.\nВведите город (или 'все'):")
    await state.set_state(TruckSearchStates.city)

async def filter_city(message: types.Message, state: FSMContext):
    await state.update_data(filter_city=message.text.strip())
    await message.answer("Введите минимальную дату начала (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(TruckSearchStates.date_from)

async def filter_date_from_truck(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        try:
            parsed = datetime.strptime(message.text, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ или 'нет'.")
            return
        await state.update_data(filter_date_from=parsed)
    else:
        await state.update_data(filter_date_from="нет")

    await message.answer("Введите максимальную дату начала (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(TruckSearchStates.date_to)

async def filter_date_to_truck(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        try:
            parsed = datetime.strptime(message.text, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ или 'нет'.")
            return
        await state.update_data(filter_date_to=parsed)
    else:
        await state.update_data(filter_date_to="нет")

    data = await state.get_data()
    fc      = data.get("filter_city", "").lower()
    fd_from = data.get("filter_date_from", "")
    fd_to   = data.get("filter_date_to", "")

    query = """
    SELECT t.id, u.name, t.city, t.region, t.date_from, t.weight, t.body_type, t.direction
    FROM trucks t
    JOIN users u ON t.user_id = u.id
    WHERE 1=1
    """
    params = []
    if fc != "все":
        query += " AND lower(t.city) = ?"
        params.append(fc)
    if fd_from != "нет":
        query += " AND date(t.date_from) >= date(?)"
        params.append(fd_from)
    if fd_to != "нет":
        query += " AND date(t.date_from) <= date(?)"
        params.append(fd_to)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("📬 По вашему запросу ТС не найдено.")
    else:
        text = "📋 Найденные ТС:\n\n"
        for r in rows:
            text += (
                f"ID: {r['id']}\n"
                f"Владелец: {r['name']}\n"
                f"{r['city']}, {r['region']}\n"
                f"Дата доступно: {r['date_from']}\n"
                f"Грузоподъёмность: {r['weight']} т, Кузов: {r['body_type']}\n"
                f"Направление: {r['direction']}\n\n"
            )
        await message.answer(text)

    await state.clear()

def register_truck_handlers(dp: Dispatcher):
    dp.message.register(cmd_add_truck, Command(commands=["add_truck"]))
    dp.message.register(process_city,       StateFilter(TruckAddStates.city))
    dp.message.register(process_region,     StateFilter(TruckAddStates.region))
    dp.message.register(process_date_from,  StateFilter(TruckAddStates.date_from))
    dp.message.register(process_date_to,    StateFilter(TruckAddStates.date_to))
    dp.message.register(process_weight,     StateFilter(TruckAddStates.weight))
    dp.message.register(process_body_type,  StateFilter(TruckAddStates.body_type))
    dp.message.register(process_direction,  StateFilter(TruckAddStates.direction))
    dp.message.register(process_route_regions, StateFilter(TruckAddStates.route_regions))
    dp.message.register(process_truck_comment,   StateFilter(TruckAddStates.comment))

    dp.message.register(cmd_find_trucks,        Command(commands=["find_trucks"]))
    dp.message.register(filter_city,            StateFilter(TruckSearchStates.city))
    dp.message.register(filter_date_from_truck, StateFilter(TruckSearchStates.date_from))
    dp.message.register(filter_date_to_truck,   StateFilter(TruckSearchStates.date_to))
