# handlers/truck.py

from aiogram import types, Dispatcher
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db import get_connection
from datetime import datetime

# 1) Определяем состояния для добавления ТС
class TruckStates(StatesGroup):
    city            = State()
    region          = State()
    date_from       = State()
    date_to         = State()
    weight          = State()
    body_type       = State()
    direction       = State()
    route_regions   = State()
    comment         = State()

# 2) Сценарий: команда /add_truck
async def cmd_add_truck(message: types.Message, state: FSMContext):
    # Проверка регистрации
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    await message.answer("🚛 Начнём добавление ТС.\nВ каком городе стоит ТС?")
    await state.set_state(TruckStates.city)

# 3) Состояние: город стоянки
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Регион стоянки:")
    await state.set_state(TruckStates.region)

# 4) Состояние: регион стоянки
async def process_region(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text)
    await message.answer("Дата доступности (c) (ДД.ММ.ГГГГ):")
    await state.set_state(TruckStates.date_from)

# 5) Состояние: дата от
async def process_date_from(message: types.Message, state: FSMContext):
    await state.update_data(date_from=message.text)
    await message.answer("Дата до (ДД.ММ.ГГГГ):")
    await state.set_state(TruckStates.date_to)

# 6) Состояние: дата до
async def process_date_to(message: types.Message, state: FSMContext):
    await state.update_data(date_to=message.text)
    await message.answer("Грузоподъёмность (в тоннах):")
    await state.set_state(TruckStates.weight)

# 7) Состояние: вес
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = int(message.text)
    except ValueError:
        await message.answer("Введи грузоподъёмность цифрой (например, 15):")
        return

    await state.update_data(weight=weight)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Тент")],
            [types.KeyboardButton(text="Рефрижератор")],
            [types.KeyboardButton(text="Изотерм")],
            [types.KeyboardButton(text="Любой")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выбери тип кузова ТС:", reply_markup=kb)
    await state.set_state(TruckStates.body_type)

# 8) Состояние: тип кузова
async def process_body_type(message: types.Message, state: FSMContext):
    await state.update_data(body_type=message.text)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Ищу заказ", callback_data="direction_order")],
            [types.InlineKeyboardButton(text="Попутный транспорт", callback_data="direction_extra")]
        ]
    )
    await message.answer("Выбери направление:", reply_markup=kb)
    await state.set_state(TruckStates.direction)

# 9) Состояние: направление
async def process_direction(message: types.Message, state: FSMContext):
    await state.update_data(direction=message.text)
    await message.answer("Перечисли через запятую регионы, где готов ехать (или 'нет'):")
    await state.set_state(TruckStates.route_regions)

# 10) Состояние: регионы маршрута
async def process_route_regions(message: types.Message, state: FSMContext):
    regions_input = message.text
    regions = regions_input if regions_input.lower() != "нет" else ""
    await state.update_data(route_regions=regions)
    await message.answer("Добавь комментарий (или напиши 'нет'):")
    await state.set_state(TruckStates.comment)

# 11) Состояние: комментарий и сохранение
async def process_truck_comment(message: types.Message, state: FSMContext):
    comment = message.text if message.text.lower() != "нет" else ""
    data = await state.get_data()

    # Получаем user_id
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

    # Вставляем запись о ТС
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

# 12) Команда /find_trucks: начать поиск ТС по фильтрам
async def cmd_find_trucks(message: types.Message, state: FSMContext):
    # Проверяем регистрацию
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    # Запрашиваем город, где нужен ТС
    await message.answer("🔍 Поиск ТС.\nВведите город (или 'все'):")
    await state.set_state(TruckStates.city)

# 13) После ввода города
async def filter_city(message: types.Message, state: FSMContext):
    await state.update_data(filter_city=message.text)
    await message.answer("Введите минимальную дату начала (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(TruckStates.date_from)

# 14) После ввода даты_from
async def filter_date_from_truck(message: types.Message, state: FSMContext):
    await state.update_data(filter_date_from=message.text)
    await message.answer("Введите максимальную дату начала (ДД.ММ.ГГГГ) или 'нет':")
    await state.set_state(TruckStates.date_to)

# 15) После ввода даты_to — выводим результаты
async def filter_date_to_truck(message: types.Message, state: FSMContext):
    data = await state.get_data()
    filter_city = data.get("filter_city")
    filter_date_from = data.get("filter_date_from")
    filter_date_to = message.text

    # Составляем SQL-запрос
    query = "SELECT t.id, u.name, t.city, t.region, t.date_from, t.weight, t.body_type, t.direction FROM trucks t JOIN users u ON t.user_id = u.id WHERE 1=1"
    params = []

    if filter_city.lower() != "все":
        query += " AND t.city = ?"
        params.append(filter_city)
    if filter_date_from.lower() != "нет":
        query += " AND date(t.date_from, 'start of day') >= date(?, 'start of day')"
        params.append(filter_date_from)
    if filter_date_to.lower() != "нет":
        query += " AND date(t.date_from, 'start of day') <= date(?, 'start of day')"
        params.append(filter_date_to)

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

# 16) Регистрация хендлеров в этом модуле
def register_truck_handlers(dp: Dispatcher):
    dp.message.register(cmd_add_truck, Command(commands=["add_truck"]))
    dp.message.register(process_city, StateFilter(TruckStates.city))
    dp.message.register(process_region, StateFilter(TruckStates.region))
    dp.message.register(process_date_from, StateFilter(TruckStates.date_from))
    dp.message.register(process_date_to, StateFilter(TruckStates.date_to))
    dp.message.register(process_weight, StateFilter(TruckStates.weight))
    dp.message.register(process_body_type, StateFilter(TruckStates.body_type))
    dp.message.register(process_direction, StateFilter(TruckStates.direction))
    dp.message.register(process_route_regions, StateFilter(TruckStates.route_regions))
    dp.message.register(process_truck_comment, StateFilter(TruckStates.comment))

    dp.message.register(cmd_find_trucks, Command(commands=["find_trucks"]))
    dp.message.register(filter_city, StateFilter(TruckStates.city))
    dp.message.register(filter_date_from_truck, StateFilter(TruckStates.date_from))
    dp.message.register(filter_date_to_truck, StateFilter(TruckStates.date_to))
