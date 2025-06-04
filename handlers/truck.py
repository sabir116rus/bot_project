# handlers/truck.py

from aiogram import types, Dispatcher
from aiogram.types import KeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from states import BaseStates
from datetime import datetime

from db import get_connection
from .common import (
    get_main_menu,
    ask_and_store,
    show_search_results,
    create_paged_keyboard,
)
from calendar_keyboard import generate_calendar
from utils import (
    parse_date,
    get_current_user_id,
    format_date_for_display,
    log_user_action,
    get_unique_truck_cities,
    clear_city_cache,
    validate_weight,
)
from config import Config
from locations import (
    get_regions,
    get_cities,
    get_regions_page,
    get_cities_page,
)

class TruckAddStates(BaseStates):
    region        = State()
    city          = State()
    date_from     = State()
    date_to       = State()
    weight        = State()
    body_type     = State()
    direction     = State()
    route_regions = State()
    comment       = State()


class TruckSearchStates(BaseStates):
    city          = State()
    date_from     = State()
    date_to       = State()


# ========== СЦЕНАРИЙ: ДОБАВЛЕНИЕ ТС ==========

async def cmd_start_add_truck(message: types.Message, state: FSMContext):
    user_id = await get_current_user_id(message)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    page = 0
    regions, _, has_next = get_regions_page(page)
    kb = create_paged_keyboard(regions, False, has_next)
    await ask_and_store(
        message,
        state,
        "🚛 Начнём добавление ТС.\nВыберите регион стоянки:",
        TruckAddStates.region,
        reply_markup=kb,
    )
    await state.update_data(r_page=page)


async def process_region(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    page = data.get("r_page", 0)

    if text == "Вперёд":
        page += 1
    elif text == "Назад":
        page = max(page - 1, 0)
    if text in {"Вперёд", "Назад"}:
        regions, has_prev, has_next = get_regions_page(page)
        kb = create_paged_keyboard(regions, has_prev, has_next)
        await ask_and_store(
            message,
            state,
            "Выберите регион стоянки:",
            TruckAddStates.region,
            reply_markup=kb,
        )
        await state.update_data(r_page=page)
        return

    if text not in get_regions():
        await message.answer("Пожалуйста, выбери регион из списка.")
        return

    await state.update_data(region=text)
    cities = get_cities(text)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c)] for c in cities],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    cpage = 0
    cities, _, has_next = get_cities_page(text, cpage)
    kb = create_paged_keyboard(cities, False, has_next)
    await ask_and_store(
        message,
        state,
        "В каком городе стоит ТС?",
        TruckAddStates.city,
        reply_markup=kb,
    )
    await state.update_data(c_page=cpage)


async def process_city(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    page = data.get("c_page", 0)
    region = data.get("region")

    if text == "Вперёд":
        page += 1
    elif text == "Назад":
        page = max(page - 1, 0)
    if text in {"Вперёд", "Назад"}:
        cities, has_prev, has_next = get_cities_page(region, page)
        kb = create_paged_keyboard(cities, has_prev, has_next)
        await ask_and_store(
            message,
            state,
            "В каком городе стоит ТС?",
            TruckAddStates.city,
            reply_markup=kb,
        )
        await state.update_data(c_page=page)
        return

    await state.update_data(city=text)
    await ask_and_store(
        message,
        state,
        "Дата доступности (с):",
        TruckAddStates.date_from,
        reply_markup=generate_calendar(),
    )
    await state.update_data(
        calendar_field="date_from",
        calendar_next_state=TruckAddStates.date_to,
        calendar_next_text="Дата доступности (по):",
        calendar_next_markup=generate_calendar(),
    )


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
        "Дата доступности (по):",
        TruckAddStates.date_to,
        reply_markup=generate_calendar(),
    )
    await state.update_data(
        calendar_field="date_to",
        calendar_next_state=TruckAddStates.weight,
        calendar_next_text="Грузоподъёмность (в тоннах):",
        calendar_next_markup=None,
    )


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
    await state.update_data(calendar_field=None)


async def process_date_from_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_from selection from calendar."""
    date_iso = callback.data.split(":", 1)[1]
    await state.update_data(date_from=date_iso)
    await callback.message.delete()
    bot_msg = await callback.message.answer(
        "Дата доступности (по):", reply_markup=generate_calendar()
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="date_to",
    )
    await state.set_state(TruckAddStates.date_to)
    await callback.answer()


async def process_date_to_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_to selection from calendar."""
    date_iso = callback.data.split(":", 1)[1]
    data = await state.get_data()
    df_iso = data.get("date_from")
    dt_from = datetime.strptime(df_iso, "%Y-%m-%d") if df_iso else None
    dt_to = datetime.strptime(date_iso, "%Y-%m-%d")
    if dt_from and dt_to < dt_from:
        await callback.answer("Неверная дата", show_alert=True)
        return
    await state.update_data(date_to=date_iso, calendar_field=None)
    await callback.message.delete()
    bot_msg = await callback.message.answer(
        "Грузоподъёмность (в тоннах):"
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
    await state.set_state(TruckAddStates.weight)
    await callback.answer()


async def process_weight(message: types.Message, state: FSMContext):
    """Store truck weight after validating the input."""
    raw = message.text.strip()
    ok, weight = validate_weight(raw)
    if not ok:
        await message.answer(
            "Введи грузоподъёмность от 1 до 1000 тонн цифрой (например, 15):"
        )
        return

    await state.update_data(weight=weight)

    kb_buttons = [[KeyboardButton(text=bt)] for bt in Config.BODY_TYPES]
    kb_buttons.append([KeyboardButton(text="Любой")])
    kb = types.ReplyKeyboardMarkup(
        keyboard=kb_buttons,
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


async def process_body_type(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in (Config.BODY_TYPES + ["Любой"]):
        await message.answer("Пожалуйста, нажми одну из кнопок: «Рефрижератор», «Тент», «Изотерм» или «Любой».")
        return

    await state.update_data(body_type=text)

    kb = types.ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=opt)] for opt in Config.TRUCK_DIRECTIONS],
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


async def process_direction(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in Config.TRUCK_DIRECTIONS:
        await message.answer("Пожалуйста, нажми «Ищу заказ» или «Попутный путь».")
        return

    await state.update_data(direction=text)
    await ask_and_store(
        message,
        state,
        "Перечисли через запятую регионы, где готов ехать (или 'нет'):",
        TruckAddStates.route_regions
    )


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

    clear_city_cache()

    await message.answer("✅ ТС успешно добавлено!", reply_markup=get_main_menu())
    log_user_action(user_id, "truck_added")
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

    # Получаем уникальные города стоянки
    cities = get_unique_truck_cities()

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

    # Спрашиваем минимальную дату начала
    bot_msg = await message.answer(
        "Минимальная дата начала:",
        reply_markup=generate_calendar(include_skip=True)
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="filter_date_from",
        calendar_next_state=TruckSearchStates.date_to,
        calendar_next_text="Максимальная дата начала:",
        calendar_next_markup=generate_calendar(include_skip=True),
    )
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
        "Максимальная дата начала:",
        reply_markup=generate_calendar(include_skip=True)
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="filter_date_to",
        calendar_next_state=TruckSearchStates.date_to,
        calendar_next_text="",
        calendar_next_markup=None,
    )
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
    user_id = await get_current_user_id(message)
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
        await show_search_results(message, rows)

    log_user_action(user_id, "truck_search", f"results={len(rows)}")
    await state.clear()


async def filter_date_from_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_from selection for truck search."""
    if callback.data == "cal:skip":
        await state.update_data(filter_date_from="нет")
    else:
        val = callback.data.split(":", 1)[1]
        await state.update_data(filter_date_from=val)
    await callback.message.delete()
    bot_msg = await callback.message.answer(
        "Максимальная дата начала:",
        reply_markup=generate_calendar(include_skip=True)
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="filter_date_to",
    )
    await state.set_state(TruckSearchStates.date_to)
    await callback.answer()


async def filter_date_to_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_to selection for truck search and show results."""
    if callback.data == "cal:skip":
        await state.update_data(filter_date_to="нет")
    else:
        val = callback.data.split(":", 1)[1]
        await state.update_data(filter_date_to=val)

    data = await state.get_data()
    user_id = await get_current_user_id(callback.message)
    fc = data.get("filter_city", "")
    fd_from = data.get("filter_date_from", "")
    fd_to = data.get("filter_date_to", "")

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

    await callback.message.delete()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await callback.message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    if not rows:
        await callback.message.answer("📬 По вашему запросу ТС не найдено.", reply_markup=get_main_menu())
    else:
        await show_search_results(callback.message, rows)

    log_user_action(user_id, "truck_search", f"results={len(rows)}")
    await state.clear()

def register_truck_handlers(dp: Dispatcher):
    # Добавление ТС (без изменений)
    dp.message.register(cmd_start_add_truck, lambda m: m.text == "➕ Добавить ТС")
    dp.message.register(process_region,        StateFilter(TruckAddStates.region))
    dp.message.register(process_city,          StateFilter(TruckAddStates.city))
    dp.message.register(process_date_from,     StateFilter(TruckAddStates.date_from))
    dp.message.register(process_date_to,       StateFilter(TruckAddStates.date_to))
    dp.callback_query.register(
        process_date_from_cb,
        StateFilter(TruckAddStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        process_date_to_cb,
        StateFilter(TruckAddStates.date_to),
        lambda c: c.data.startswith("cal:")
    )
    dp.message.register(process_weight,        StateFilter(TruckAddStates.weight))
    dp.message.register(process_body_type,     StateFilter(TruckAddStates.body_type))
    dp.message.register(process_direction,     StateFilter(TruckAddStates.direction))
    dp.message.register(process_route_regions, StateFilter(TruckAddStates.route_regions))
    dp.message.register(process_truck_comment, StateFilter(TruckAddStates.comment))

    dp.message.register(cmd_start_find_trucks,       lambda m: m.text == "🔍 Найти ТС")
    dp.message.register(filter_city,                 StateFilter(TruckSearchStates.city))
    dp.message.register(filter_date_from_truck,      StateFilter(TruckSearchStates.date_from))
    dp.message.register(filter_date_to_truck,        StateFilter(TruckSearchStates.date_to))
    dp.callback_query.register(
        filter_date_from_cb,
        StateFilter(TruckSearchStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        filter_date_to_cb,
        StateFilter(TruckSearchStates.date_to),
        lambda c: c.data.startswith("cal:")
    )
