# handlers/truck.py

from aiogram import types, Dispatcher
from aiogram.types import KeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from db import get_connection
from .common import get_main_menu, ask_and_store
from utils import (
    parse_date,
    get_current_user_id,
    format_date_for_display,
    show_progress,
)


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


# ========== СЦЕНАРИЙ: ДОБАВЛЕНИЕ ТС ==========

async def cmd_start_add_truck(message: types.Message, state: FSMContext):
    user_id = await get_current_user_id(message)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    await message.answer(
        "🚛 Начнём добавление ТС.\nВ каком городе стоит ТС?",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await show_progress(message, 1, 9)
    await state.set_state(TruckAddStates.city)


async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await ask_and_store(
        message,
        state,
        "Регион стоянки:",
        TruckAddStates.region
    )
    await show_progress(message, 2, 9)


async def process_region(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text.strip())
    await ask_and_store(
        message,
        state,
        "Дата доступности (с) (ДД.MM.ГГГГ):",
        TruckAddStates.date_from
    )
    await show_progress(message, 3, 9)


async def process_date_from(message: types.Message, state: FSMContext):
    raw = message.text.strip()
    parsed = parse_date(raw)
    if not parsed:
        await message.answer("Неверный формат даты. Введите ДД.MM.ГГГГ:")
        return

    await state.update_data(date_from=parsed)
    await ask_and_store(
        message,
        state,
        "Дата доступности (по) (ДД.MM.ГГГГ):",
        TruckAddStates.date_to
    )
    await show_progress(message, 4, 9)


async def process_date_to(message: types.Message, state: FSMContext):
    raw = message.text.strip()
    parsed_to = parse_date(raw)
    if not parsed_to:
        await message.answer("Неверный формат даты. Введите ДД.MM.ГГГГ:")
        return

    data = await state.get_data()
    df_iso = data.get("date_from")
    dt_from = datetime.strptime(df_iso, "%Y-%m-%d") if df_iso else None

    dt_to = datetime.strptime(parsed_to, "%Y-%m-%d")
    if dt_from and dt_to < dt_from:
        await message.answer("Дата «по» не может быть раньше даты «с». Повторите ввод:")
        return

    await state.update_data(date_to=parsed_to)
    await ask_and_store(
        message,
        state,
        "Грузоподъёмность (в тоннах):",
        TruckAddStates.weight
    )
    await show_progress(message, 5, 9)


async def process_weight(message: types.Message, state: FSMContext):
    raw = message.text.strip()
    try:
        weight = int(raw)
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
    await ask_and_store(
        message,
        state,
        "Выбери тип кузова ТС:",
        TruckAddStates.body_type,
        reply_markup=kb
    )
    await show_progress(message, 6, 9)


async def process_body_type(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in ("Рефрижератор", "Тент", "Изотерм", "Любой"):
        await message.answer("Пожалуйста, нажми одну из кнопок: «Рефрижератор», «Тент», «Изотерм» или «Любой».")
        return

    await state.update_data(body_type=text)

    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ищу заказ")],
            [KeyboardButton(text="Попутный путь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await ask_and_store(
        message,
        state,
        "Выбери направление:",
        TruckAddStates.direction,
        reply_markup=kb
    )
    await show_progress(message, 7, 9)


async def process_direction(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in ("Ищу заказ", "Попутный путь"):
        await message.answer("Пожалуйста, нажми «Ищу заказ» или «Попутный путь».")
        return

    await state.update_data(direction=text)
    await ask_and_store(
        message,
        state,
        "Перечисли через запятую регионы, где готов ехать (или 'нет'):",
        TruckAddStates.route_regions
    )
    await show_progress(message, 8, 9)


async def process_route_regions(message: types.Message, state: FSMContext):
    text = message.text.strip()
    regions = text if text.lower() != "нет" else ""
    await state.update_data(route_regions=regions)
    await ask_and_store(
        message,
        state,
        "Добавь комментарий (или напиши 'нет'):",
        TruckAddStates.comment
    )
    await show_progress(message, 9, 9)


async def process_truck_comment(message: types.Message, state: FSMContext):
    text = message.text.strip()
    comment = text if text.lower() != "нет" else ""
    data = await state.get_data()

    required = ["city", "region", "date_from", "date_to", "weight", "body_type", "direction", "route_regions"]
    if not all(k in data for k in required):
        await message.answer("Что-то пошло не так. Попробуй «➕ Добавить ТС» ещё раз.")
        await state.clear()
        return

    user_id = await get_current_user_id(message)
    if not user_id:
        await message.answer("Не удалось найти профиль. Сначала /start.")
        await state.clear()
        return

    # Удаляем сообщение пользователя с комментарием
    await message.delete()
    # Удаляем последний бот-вопрос
    bot_data = await state.get_data()
    last_bot_msg_id = bot_data.get("last_bot_message_id")
    if last_bot_msg_id:
        try:
            await message.chat.delete_message(last_bot_msg_id)
        except Exception:
            pass

    # Вставляем запись в БД
    with get_connection() as conn:
        cursor = conn.cursor()
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

    await message.answer("✅ ТС успешно добавлено!", reply_markup=get_main_menu())
    await state.clear()

# ========== СЦЕНАРИЙ: ПОИСК ТС С КНОПКАМИ ==========

async def cmd_start_find_trucks(message: types.Message, state: FSMContext):
    """
    Запускает поиск ТС. Вместо свободного текста выдаёт клавиатуру
    со всеми возможными городами стоянки (из таблицы trucks) + кнопку "Все".
    """
    user_id = await get_current_user_id(message)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    # Удаляем сообщение-инициатор (нажатие "🔍 Найти ТС")
    await message.delete()

    # Получаем уникальные города стоянки из таблицы trucks
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT city FROM trucks WHERE city IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    cities = [r["city"] for r in rows if r["city"].strip()]
    cities.sort(key=lambda x: x.lower())

    kb_buttons = [[types.KeyboardButton(text=city)] for city in cities]
    kb_buttons.append([types.KeyboardButton(text="Все")])

    kb = types.ReplyKeyboardMarkup(
        keyboard=kb_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    bot_msg = await message.answer(
        "🔍 Поиск ТС.\nВыберите город (или нажмите «Все»):",
        reply_markup=kb
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
    await state.set_state(TruckSearchStates.city)

async def filter_city(message: types.Message, state: FSMContext):
    """
    Обработчик выбора города (или 'Все') для поиска ТС.
    Затем спрашивает минимальную дату начала.
    """
    selected = message.text.strip()
    await state.update_data(filter_city=selected.lower())

    # Удаляем сообщение пользователя и предыдущее сообщение бота
    await message.delete()
    data = await state.get_data()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    # Спрашиваем минимальную дату начала (ДД.MM.ГГГГ) или 'нет'
    bot_msg = await message.answer(
        "Введите минимальную дату начала (ДД.MM.ГГГГ) или «нет»:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
    await state.set_state(TruckSearchStates.date_from)

async def filter_date_from_truck(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        parsed = parse_date(message.text.strip())
        if not parsed:
            await message.answer("Неверный формат. Введите ДД.MM.ГГГГ или «нет».")
            return
        await state.update_data(filter_date_from=parsed)
    else:
        await state.update_data(filter_date_from="нет")

    # Удаляем сообщение пользователя и предыдущий бот-вопрос
    await message.delete()
    data = await state.get_data()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    # Спрашиваем максимальную дату начала
    bot_msg = await message.answer(
        "Введите максимальную дату начала (ДД.MM.ГГГГ) или «нет»:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
    await state.set_state(TruckSearchStates.date_to)

async def filter_date_to_truck(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        parsed = parse_date(message.text.strip())
        if not parsed:
            await message.answer("Неверный формат. Введите ДД.MM.ГГГГ или «нет».")
            return
        await state.update_data(filter_date_to=parsed)
    else:
        await state.update_data(filter_date_to="нет")

    data = await state.get_data()
    fc = data.get("filter_city", "")
    fd_from = data.get("filter_date_from", "")
    fd_to = data.get("filter_date_to", "")

    # Составляем SQL-запрос с учётом фильтров
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

    # Удаляем последнее сообщение пользователя и предыдущий бот-вопрос
    await message.delete()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    if not rows:
        await message.answer("📬 По вашему запросу ТС не найдено.", reply_markup=get_main_menu())
    else:
        text = "📋 Найденные ТС:\n\n"
        for r in rows:
            date_disp = format_date_for_display(r["date_from"])
            text += (
                f"ID: {r['id']}\n"
                f"Владелец: {r['name']}\n"
                f"{r['city']}, {r['region']}\n"
                f"Дата доступно: {date_disp}\n"
                f"Грузоподъёмность: {r['weight']} т, Кузов: {r['body_type']}\n"
                f"Направление: {r['direction']}\n\n"
            )
        await message.answer(text, reply_markup=get_main_menu())

    await state.clear()

def register_truck_handlers(dp: Dispatcher):
    # Добавление ТС (без изменений)
    dp.message.register(cmd_start_add_truck, lambda m: m.text == "➕ Добавить ТС")
    dp.message.register(process_city,          StateFilter(TruckAddStates.city))
    dp.message.register(process_region,        StateFilter(TruckAddStates.region))
    dp.message.register(process_date_from,     StateFilter(TruckAddStates.date_from))
    dp.message.register(process_date_to,       StateFilter(TruckAddStates.date_to))
    dp.message.register(process_weight,        StateFilter(TruckAddStates.weight))
    dp.message.register(process_body_type,     StateFilter(TruckAddStates.body_type))
    dp.message.register(process_direction,     StateFilter(TruckAddStates.direction))
    dp.message.register(process_route_regions, StateFilter(TruckAddStates.route_regions))
    dp.message.register(process_truck_comment, StateFilter(TruckAddStates.comment))

    dp.message.register(cmd_start_find_trucks,       lambda m: m.text == "🔍 Найти ТС")
    dp.message.register(filter_city,                 StateFilter(TruckSearchStates.city))
    dp.message.register(filter_date_from_truck,      StateFilter(TruckSearchStates.date_from))
    dp.message.register(filter_date_to_truck,        StateFilter(TruckSearchStates.date_to))
