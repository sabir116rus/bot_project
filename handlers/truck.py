"""Handlers for truck addition and search workflows."""

from aiogram import types, Dispatcher
from aiogram.types import KeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from states import BaseStates, TruckEditStates
from datetime import datetime

from db import (
    get_connection,
    update_truck_weight,
    update_truck_route,
    update_truck_dates,
    delete_truck,
    get_truck,
)
from .common import (
    get_main_menu,
    ask_and_store,
    show_search_results,
    process_weight_step,
    parse_and_store_date,
)

from calendar_keyboard import generate_calendar, handle_calendar_callback
from utils import (
    get_current_user_id,
    format_date_for_display,
    log_user_action,
    get_unique_truck_cities,
    clear_city_cache,
    validate_weight,
)
from locations import (
    get_regions,
    get_cities,
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

    # Сразу показываем все регионы (без пагинации)
    regions = get_regions()
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=region)] for region in regions],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await ask_and_store(
        message,
        state,
        "🚛 Начнём добавление ТС.\nВыберите регион стоянки:",
        TruckAddStates.region,
        reply_markup=kb,
    )


async def process_region(message: types.Message, state: FSMContext):
    text = message.text.strip()
    all_regions = get_regions()
    if text not in all_regions:
        await message.answer("Пожалуйста, выбери регион из списка.")
        return

    await state.update_data(region=text)
    # Показываем все города выбранного региона
    cities = get_cities(text)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=city)] for city in cities],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await ask_and_store(
        message,
        state,
        "В каком городе стоит ТС?",
        TruckAddStates.city,
        reply_markup=kb,
    )


async def process_city(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    region = data.get("region")
    if not region:
        # Если state потерялся, просим начать заново
        await message.answer("Попробуйте снова: выберите регион стоянки.")
        await state.clear()
        return

    cities = get_cities(region)
    if text not in cities:
        await message.answer("Пожалуйста, выбери город из списка.")
        return

    await state.update_data(city=text)
    # Переходим к выбору даты доступности "с"
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
        calendar_include_skip=False,
    )


async def process_date_from(message: types.Message, state: FSMContext):
    ok = await parse_and_store_date(
        message,
        state,
        "date_from",
        "Неверный формат даты. Введите ДД.MM.ГГГГ:",
    )
    if not ok:
        return
    # Запрашиваем дату доступности "по"
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
        calendar_include_skip=False,
    )


async def process_date_to(message: types.Message, state: FSMContext):
    ok = await parse_and_store_date(
        message,
        state,
        "date_to",
        "Неверный формат даты. Введите ДД.MM.ГГГГ:",
        compare_field="date_from",
        compare_error="Дата «по» не может быть раньше даты «с». Повторите ввод:",
    )
    if not ok:
        return
    # Запрашиваем грузоподъёмность
    await ask_and_store(
        message,
        state,
        "Грузоподъёмность (в тоннах):",
        TruckAddStates.weight
    )
    await state.update_data(calendar_field=None)

async def process_weight(message: types.Message, state: FSMContext):
    """Store truck weight after validating the input."""
    await process_weight_step(
        message,
        state,
        TruckAddStates.body_type,
        "Выбери тип кузова ТС:",
        "Любой",
        "Введи грузоподъёмность от 1 до 1000 тонн цифрой (например, 15):",
        validate_func=validate_weight,
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
        calendar_include_skip=True,
    )
    await state.set_state(TruckSearchStates.date_from)


async def filter_date_from_truck(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        ok = await parse_and_store_date(
            message,
            state,
            "filter_date_from",
            "Неверный формат. Введите ДД.MM.ГГГГ или «нет».",
        )
        if not ok:
            return
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
        calendar_include_skip=True,
    )
    await state.set_state(TruckSearchStates.date_to)


async def filter_date_to_truck(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        ok = await parse_and_store_date(
            message,
            state,
            "filter_date_to",
            "Неверный формат. Введите ДД.MM.ГГГГ или «нет».",
        )
        if not ok:
            return
    else:
        await state.update_data(filter_date_to="нет")

    data = await state.get_data()
    user_id = await get_current_user_id(message)
    fc = data.get("filter_city", "")
    fd_from = data.get("filter_date_from", "")
    fd_to = data.get("filter_date_to", "")

    # Составляем SQL-запрос с учётом фильтров
    base_query = """
    SELECT t.id, u.name, t.city, t.region, t.date_from, t.weight, t.body_type, t.direction
    FROM trucks t
    JOIN users u ON t.user_id = u.id
    WHERE 1=1
    """
    filters = [
        (fc if fc != "все" else None, " AND lower(t.city) = ?"),
        (fd_from if fd_from != "нет" else None, " AND date(t.date_from) >= date(?)"),
        (fd_to if fd_to != "нет" else None, " AND date(t.date_from) <= date(?)"),
    ]
    query, params = build_search_query(base_query, filters)

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


# ========== СЦЕНАРИЙ: РЕДАКТИРОВАНИЕ/УДАЛЕНИЕ ТС ==========

async def handle_edit_truck(callback: types.CallbackQuery):
    """Show edit options for selected truck."""
    truck_id = int(callback.data.split(":")[1])
    row = get_truck(truck_id)
    if not row:
        await callback.answer()
        return
    text = (
        f"ТС ID {row['id']}\n"
        f"{row['city']} ({row['region']})\n"
        f"{format_date_for_display(row['date_from'])} - "
        f"{format_date_for_display(row['date_to'])}\n"
        f"Вес: {row['weight']} т"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Маршрут", callback_data=f"edit_truck_route:{row['id']}")],
            [types.InlineKeyboardButton(text="Даты", callback_data=f"edit_truck_dates:{row['id']}")],
            [types.InlineKeyboardButton(text="Вес", callback_data=f"edit_truck_weight:{row['id']}")],
        ]
    )
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


async def start_edit_truck_weight(callback: types.CallbackQuery, state: FSMContext):
    truck_id = int(callback.data.split(":")[1])
    await state.update_data(edit_truck_id=truck_id)
    await callback.message.answer("Новый вес (тонны):")
    await state.set_state(TruckEditStates.weight)
    await callback.answer()


async def start_edit_truck_route(callback: types.CallbackQuery, state: FSMContext):
    truck_id = int(callback.data.split(":")[1])
    await state.update_data(edit_truck_id=truck_id)
    await callback.message.answer("Новый маршрут:")
    await state.set_state(TruckEditStates.route)
    await callback.answer()


async def start_edit_truck_dates(callback: types.CallbackQuery, state: FSMContext):
    truck_id = int(callback.data.split(":")[1])
    await state.update_data(edit_truck_id=truck_id)
    await callback.message.answer("Новая дата отправления (ГГГГ-ММ-ДД):")
    await state.set_state(TruckEditStates.date_from)
    await callback.answer()


async def process_edit_truck_weight(message: types.Message, state: FSMContext):
    """Validate and store new truck weight."""
    ok, weight = validate_weight(message.text)
    if not ok:
        await message.answer("Введите число от 1 до 1000:")
        return
    data = await state.get_data()
    tid = data.get("edit_truck_id")
    if tid:
        update_truck_weight(tid, weight)
        clear_city_cache()
    await message.answer("Запись обновлена.", reply_markup=get_main_menu())
    await state.clear()


async def process_edit_truck_route(message: types.Message, state: FSMContext):
    """Update truck route."""
    data = await state.get_data()
    tid = data.get("edit_truck_id")
    if tid:
        update_truck_route(tid, message.text.strip())
    await message.answer("Маршрут обновлён.", reply_markup=get_main_menu())
    await state.clear()


async def process_edit_truck_date_from(message: types.Message, state: FSMContext):
    """Store new start date for truck."""
    await state.update_data(new_date_from=message.text.strip())
    await message.answer("Новая дата окончания (ГГГГ-ММ-ДД):")
    await state.set_state(TruckEditStates.date_to)


async def process_edit_truck_date_to(message: types.Message, state: FSMContext):
    """Update truck dates."""
    data = await state.get_data()
    tid = data.get("edit_truck_id")
    df = data.get("new_date_from")
    if tid and df:
        update_truck_dates(tid, df, message.text.strip())
    await message.answer("Даты обновлены.", reply_markup=get_main_menu())
    await state.clear()


async def handle_delete_truck(callback: types.CallbackQuery):
    """Delete truck entry and inform the user."""
    truck_id = int(callback.data.split(":")[1])
    delete_truck(truck_id)
    clear_city_cache()
    await callback.answer("Удалено")
    await callback.message.delete()




def register_truck_handlers(dp: Dispatcher):
    # Добавление ТС
    dp.message.register(cmd_start_add_truck, lambda m: m.text == "➕ Добавить ТС")
    dp.message.register(process_region,        StateFilter(TruckAddStates.region))
    dp.message.register(process_city,          StateFilter(TruckAddStates.city))
    dp.message.register(process_date_from,     StateFilter(TruckAddStates.date_from))
    dp.message.register(process_date_to,       StateFilter(TruckAddStates.date_to))
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(TruckAddStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(TruckAddStates.date_to),
        lambda c: c.data.startswith("cal:")
    )
    dp.message.register(process_weight,        StateFilter(TruckAddStates.weight))
    dp.message.register(process_body_type,     StateFilter(TruckAddStates.body_type))
    dp.message.register(process_direction,     StateFilter(TruckAddStates.direction))
    dp.message.register(process_route_regions, StateFilter(TruckAddStates.route_regions))
    dp.message.register(process_truck_comment, StateFilter(TruckAddStates.comment))

    # Поиск ТС
    dp.message.register(cmd_start_find_trucks,       lambda m: m.text == "🔍 Найти ТС")
    dp.message.register(filter_city,                 StateFilter(TruckSearchStates.city))
    dp.message.register(filter_date_from_truck,      StateFilter(TruckSearchStates.date_from))
    dp.message.register(filter_date_to_truck,        StateFilter(TruckSearchStates.date_to))
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(TruckSearchStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(TruckSearchStates.date_to),
        lambda c: c.data.startswith("cal:")
    )

    # Редактирование и удаление
    dp.callback_query.register(
        handle_edit_truck,
        lambda c: c.data.startswith("edit_truck:"),
    )
    dp.callback_query.register(
        start_edit_truck_route,
        lambda c: c.data.startswith("edit_truck_route:"),
    )
    dp.callback_query.register(
        start_edit_truck_dates,
        lambda c: c.data.startswith("edit_truck_dates:"),
    )
    dp.callback_query.register(
        start_edit_truck_weight,
        lambda c: c.data.startswith("edit_truck_weight:"),
    )
    dp.callback_query.register(
        handle_delete_truck,
        lambda c: c.data.startswith("del_truck:"),
    )
    dp.message.register(
        process_edit_truck_weight,
        StateFilter(TruckEditStates.weight),
    )
    dp.message.register(
        process_edit_truck_route,
        StateFilter(TruckEditStates.route),
    )
    dp.message.register(
        process_edit_truck_date_from,
        StateFilter(TruckEditStates.date_from),
    )
    dp.message.register(
        process_edit_truck_date_to,
        StateFilter(TruckEditStates.date_to),
    )
