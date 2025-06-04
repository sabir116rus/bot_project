# handlers/cargo.py

from aiogram import types, Dispatcher
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
    show_progress,
    log_user_action,
    get_unique_cities_from,
    get_unique_cities_to,
    clear_city_cache,
    validate_weight,
)
from locations import (
    get_regions,
    get_cities,
    get_regions_page,
    get_cities_page,
)
from config import Config

class CargoAddStates(BaseStates):
    region_from  = State()
    city_from    = State()
    region_to    = State()
    city_to      = State()
    date_from    = State()
    date_to      = State()
    weight       = State()
    body_type    = State()
    is_local     = State()
    comment      = State()


class CargoSearchStates(BaseStates):
    city_from    = State()
    city_to      = State()
    date_from    = State()
    date_to      = State()


# ========== СЦЕНАРИЙ: ДОБАВЛЕНИЕ ГРУЗА ==========

async def cmd_start_add_cargo(message: types.Message, state: FSMContext):
    user_id = await get_current_user_id(message)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    # Удаляем любое предыдущее сообщение (если требуется)
    page = 0
    regions, _, has_next = get_regions_page(page)
    kb = create_paged_keyboard(regions, False, has_next)
    await show_progress(message, state, 1, 10)
    await ask_and_store(
        message,
        state,
        "📦 Начнём добавление груза.\nВыбери регион отправления:",
        CargoAddStates.region_from,
        reply_markup=kb,
    )
    await state.update_data(rf_page=page)


async def process_region_from(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    page = data.get("rf_page", 0)

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
            "Выбери регион отправления:",
            CargoAddStates.region_from,
            reply_markup=kb,
        )
        await state.update_data(rf_page=page)
        return

    if text not in get_regions():
        await message.answer("Пожалуйста, выбери регион из списка.")
        return

    await state.update_data(region_from=text)

    cpage = 0
    cities, _, has_next = get_cities_page(text, cpage)
    kb = create_paged_keyboard(cities, False, has_next)

    await show_progress(message, state, 2, 10)
    await ask_and_store(
        message,
        state,
        "Откуда (город):",
        CargoAddStates.city_from,
        reply_markup=kb,
    )
    await state.update_data(cf_page=cpage)


async def process_city_from(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    page = data.get("cf_page", 0)
    region = data.get("region_from")

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
            "Откуда (город):",
            CargoAddStates.city_from,
            reply_markup=kb,
        )
        await state.update_data(cf_page=page)
        return

    await state.update_data(city_from=text)

    rpage = 0
    regions, _, has_next = get_regions_page(rpage)
    kb = create_paged_keyboard(regions, False, has_next)

    await show_progress(message, state, 3, 10)
    await ask_and_store(
        message,
        state,
        "Регион назначения:",
        CargoAddStates.region_to,
        reply_markup=kb,
    )
    await state.update_data(rt_page=rpage)


async def process_region_to(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    page = data.get("rt_page", 0)

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
            "Регион назначения:",
            CargoAddStates.region_to,
            reply_markup=kb,
        )
        await state.update_data(rt_page=page)
        return

    if text not in get_regions():
        await message.answer("Пожалуйста, выбери регион из списка.")
        return

    await state.update_data(region_to=text)

    cpage = 0
    cities, _, has_next = get_cities_page(text, cpage)
    kb = create_paged_keyboard(cities, False, has_next)

    await show_progress(message, state, 4, 10)
    await ask_and_store(
        message,
        state,
        "Куда (город):",
        CargoAddStates.city_to,
        reply_markup=kb,
    )
    await state.update_data(ct_page=cpage)


async def process_city_to(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    page = data.get("ct_page", 0)
    region = data.get("region_to")

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
            "Куда (город):",
            CargoAddStates.city_to,
            reply_markup=kb,
        )
        await state.update_data(ct_page=page)
        return

    await state.update_data(city_to=text)
    await show_progress(message, state, 5, 10)
    await ask_and_store(
        message,
        state,
        "Дата отправления:",
        CargoAddStates.date_from,
        reply_markup=generate_calendar(),
    )
    await state.update_data(
        calendar_field="date_from",
        calendar_next_state=CargoAddStates.date_to,
        calendar_next_text="Дата прибытия:",
        calendar_next_markup=generate_calendar(),
    )


async def process_date_from(message: types.Message, state: FSMContext):
    raw = message.text.strip()
    parsed = parse_date(raw)
    if not parsed:
        await message.answer("Неверный формат даты. Введите ДД.MM.ГГГГ:")
        return

    await state.update_data(date_from=parsed)
    await show_progress(message, state, 6, 10)
    await ask_and_store(
        message,
        state,
        "Дата прибытия:",
        CargoAddStates.date_to,
        reply_markup=generate_calendar(),
    )
    await state.update_data(
        calendar_field="date_to",
        calendar_next_state=CargoAddStates.weight,
        calendar_next_text="Вес (в тоннах, цифрой):",
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
        await message.answer("Дата прибытия не может быть раньше даты отправления. Повторите ввод:")
        return

    await state.update_data(date_to=parsed_to)
    await show_progress(message, state, 7, 10)
    await ask_and_store(
        message,
        state,
        "Вес (в тоннах, цифрой):",
        CargoAddStates.weight
    )
    await state.update_data(calendar_field=None)


async def process_date_from_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_from selection from the calendar."""
    date_iso = callback.data.split(":", 1)[1]
    await state.update_data(date_from=date_iso)
    await callback.message.delete()
    bot_msg = await callback.message.answer(
        "Дата прибытия:", reply_markup=generate_calendar()
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="date_to",
    )
    await state.set_state(CargoAddStates.date_to)
    await callback.answer()


async def process_date_to_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_to selection from the calendar."""
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
        "Вес (в тоннах, цифрой):"
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
    await state.set_state(CargoAddStates.weight)
    await callback.answer()


async def process_weight(message: types.Message, state: FSMContext):
    """Store cargo weight after validating the user input."""
    raw = message.text.strip()
    ok, weight = validate_weight(raw)
    if not ok:
        await message.answer(
            "Пожалуйста, введи вес от 1 до 1000 тонн цифрой (например, 12):"
        )
        return

    await state.update_data(weight=weight)

    kb_buttons = [[types.KeyboardButton(text=bt)] for bt in Config.BODY_TYPES]
    kb_buttons.append([types.KeyboardButton(text="Не важно")])
    kb = types.ReplyKeyboardMarkup(
        keyboard=kb_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await show_progress(message, state, 8, 10)
    await ask_and_store(
        message,
        state,
        "Выбери тип кузова:",
        CargoAddStates.body_type,
        reply_markup=kb
    )


async def process_body_type(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in (Config.BODY_TYPES + ["Не важно"]):
        await message.answer("Пожалуйста, нажми одну из кнопок:\n«Рефрижератор», «Тент», «Изотерм» или «Не важно».")
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
    await show_progress(message, state, 9, 10)
    await ask_and_store(
        message,
        state,
        "Внутригородской груз?",
        CargoAddStates.is_local,
        reply_markup=kb
    )


async def process_is_local(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    if not ("да" in text or "нет" in text):
        await message.answer("Пожалуйста, нажми «Да (внутригородской)» или «Нет (междугородний)».")
        return

    is_local = 1 if "да" in text else 0
    await state.update_data(is_local=is_local)
    await show_progress(message, state, 10, 10)
    await ask_and_store(
        message,
        state,
        "Добавь комментарий (или напиши 'нет'):",
        CargoAddStates.comment
    )


async def process_comment(message: types.Message, state: FSMContext):
    text = message.text.strip()
    comment = text if text.lower() != "нет" else ""
    data = await state.get_data()

    required_fields = [
        "city_from", "region_from", "city_to", "region_to",
        "date_from", "date_to", "weight", "body_type", "is_local"
    ]
    if not all(field in data for field in required_fields):
        await message.answer("Что-то пошло не так. Попробуй «➕ Добавить груз» ещё раз.")
        await state.clear()
        return

    user_id = await get_current_user_id(message)
    if not user_id:
        await message.answer("Не удалось найти профиль. Сначала /start.")
        await state.clear()
        return

    # Удаляем сообщение пользователя (с комментарием)
    await message.delete()
    # Удаляем последний бот-вопрос и прогресс
    bot_data = await state.get_data()
    last_bot_msg_id = bot_data.get("last_bot_message_id")
    if last_bot_msg_id:
        try:
            await message.chat.delete_message(last_bot_msg_id)
        except Exception:
            pass
    progress_msg_id = bot_data.get("last_progress_message_id")
    if progress_msg_id:
        try:
            await message.chat.delete_message(progress_msg_id)
        except Exception:
            pass
    await state.update_data(last_progress_message_id=None)

    # Вставляем запись в БД
    with get_connection() as conn:
        cursor = conn.cursor()
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

    clear_city_cache()

    await message.answer("✅ Груз успешно добавлен!", reply_markup=get_main_menu())
    log_user_action(user_id, "cargo_added")
    await state.clear()

# ========== СЦЕНАРИЙ: ПОИСК ГРУЗА С КНОПКАМИ ==========

async def cmd_start_find_cargo(message: types.Message, state: FSMContext):
    """
    Запускает поиск груза. Вместо свободного текста сразу выдаёт клавиатуру
    со всеми возможными городами-отправлениями + кнопку "Все".
    """
    user_id = await get_current_user_id(message)
    if not user_id:
        await message.answer("Сначала зарегистрируйся через /start.")
        return

    # Удаляем сообщение-инициатор (нажатие "🔍 Найти груз")
    await message.delete()

    # Получаем список уникальных городов отправления
    cities = get_unique_cities_from()

    # Строим клавиатуру: каждая строка — один город, и внизу кнопка "Все"
    kb_buttons = [[types.KeyboardButton(text=city)] for city in cities]
    kb_buttons.append([types.KeyboardButton(text="Все")])

    kb = types.ReplyKeyboardMarkup(
        keyboard=kb_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    bot_msg = await message.answer(
        "🔍 Поиск груза.\nВыберите город отправления (или нажмите «Все»):",
        reply_markup=kb
    )
    # Сохраняем ID последнего бот-сообщения, чтобы потом можно было его удалить
    await state.update_data(last_bot_message_id=bot_msg.message_id)

    await state.set_state(CargoSearchStates.city_from)

async def filter_city_from(message: types.Message, state: FSMContext):
    """
    Получаем город отправления (либо "Все"), далее предлагаем выбрать город назначения.
    """
    selected = message.text.strip()
    # Сохраняем выбранный фильтр
    await state.update_data(filter_city_from=selected.lower())

    # Удалим сообщение пользователя (кнопка) и предыдущий вопрос бота
    await message.delete()
    data = await state.get_data()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    # Теперь предлагаем выбрать город назначения
    to_cities = get_unique_cities_to()

    kb_buttons = [[types.KeyboardButton(text=city)] for city in to_cities]
    kb_buttons.append([types.KeyboardButton(text="Все")])

    kb = types.ReplyKeyboardMarkup(
        keyboard=kb_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    bot_msg = await message.answer(
        "Введите город назначения (или нажмите «Все»):",
        reply_markup=kb
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
    await state.set_state(CargoSearchStates.city_to)

async def filter_city_to(message: types.Message, state: FSMContext):
    """
    Получаем город назначения (либо "Все"), далее спрашиваем дату отправления (min/max).
    """
    selected = message.text.strip()
    await state.update_data(filter_city_to=selected.lower())

    # Удаляем сообщение пользователя и предыдущее бот-сообщение
    await message.delete()
    data = await state.get_data()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    # Спрашиваем минимальную дату отправления
    bot_msg = await message.answer(
        "Минимальная дата отправления:",
        reply_markup=generate_calendar(include_skip=True)
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="filter_date_from",
        calendar_next_state=CargoSearchStates.date_to,
        calendar_next_text="Максимальная дата отправления:",
        calendar_next_markup=generate_calendar(include_skip=True),
    )
    await state.set_state(CargoSearchStates.date_from)

async def filter_date_from(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        parsed = parse_date(message.text.strip())
        if not parsed:
            await message.answer("Неверный формат даты. Введите ДД.MM.ГГГГ или «нет».")
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

    # Спрашиваем максимальную дату отправления
    bot_msg = await message.answer(
        "Максимальная дата отправления:",
        reply_markup=generate_calendar(include_skip=True)
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="filter_date_to",
        calendar_next_state=CargoSearchStates.date_to,
        calendar_next_text="",
        calendar_next_markup=None,
    )
    await state.set_state(CargoSearchStates.date_to)

async def filter_date_to(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        parsed = parse_date(message.text.strip())
        if not parsed:
            await message.answer("Неверный формат даты. Введите ДД.MM.ГГГГ или «нет».")
            return
        await state.update_data(filter_date_to=parsed)
    else:
        await state.update_data(filter_date_to="нет")

    data = await state.get_data()
    user_id = await get_current_user_id(message)
    fc_from = data.get("filter_city_from", "")
    fc_to = data.get("filter_city_to", "")
    fd_from = data.get("filter_date_from", "")
    fd_to = data.get("filter_date_to", "")

    # Собираем SQL-запрос с учётом выбранных фильтров
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

    # Удаляем последнее сообщение пользователя и предыдущий бот-вопрос
    await message.delete()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    if not rows:
        await message.answer("📬 По вашему запросу ничего не найдено.", reply_markup=get_main_menu())
    else:
        await show_search_results(message, rows)

    log_user_action(user_id, "cargo_search", f"results={len(rows)}")
    await state.clear()


async def filter_date_from_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_from selection for cargo search."""
    if callback.data == "cal:skip":
        await state.update_data(filter_date_from="нет")
    else:
        value = callback.data.split(":", 1)[1]
        await state.update_data(filter_date_from=value)
    await callback.message.delete()
    bot_msg = await callback.message.answer(
        "Максимальная дата отправления:",
        reply_markup=generate_calendar(include_skip=True)
    )
    await state.update_data(
        last_bot_message_id=bot_msg.message_id,
        calendar_field="filter_date_to",
    )
    await state.set_state(CargoSearchStates.date_to)
    await callback.answer()


async def filter_date_to_cb(callback: types.CallbackQuery, state: FSMContext):
    """Handle date_to selection for cargo search and show results."""
    if callback.data == "cal:skip":
        await state.update_data(filter_date_to="нет")
    else:
        value = callback.data.split(":", 1)[1]
        await state.update_data(filter_date_to=value)

    data = await state.get_data()
    user_id = await get_current_user_id(callback.message)
    fc_from = data.get("filter_city_from", "")
    fc_to = data.get("filter_city_to", "")
    fd_from = data.get("filter_date_from", "")
    fd_to = data.get("filter_date_to", "")

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

    await callback.message.delete()
    prev_bot_id = data.get("last_bot_message_id")
    if prev_bot_id:
        try:
            await callback.message.chat.delete_message(prev_bot_id)
        except Exception:
            pass

    if not rows:
        await callback.message.answer("📬 По вашему запросу ничего не найдено.", reply_markup=get_main_menu())
    else:
        await show_search_results(callback.message, rows)

    log_user_action(user_id, "cargo_search", f"results={len(rows)}")
    await state.clear()

def register_cargo_handlers(dp: Dispatcher):
    # Добавление груза (осталось без изменений)
    dp.message.register(cmd_start_add_cargo, lambda m: m.text == "➕ Добавить груз")
    dp.message.register(process_region_from, StateFilter(CargoAddStates.region_from))
    dp.message.register(process_city_from,   StateFilter(CargoAddStates.city_from))
    dp.message.register(process_region_to,   StateFilter(CargoAddStates.region_to))
    dp.message.register(process_city_to,     StateFilter(CargoAddStates.city_to))
    dp.message.register(process_date_from,   StateFilter(CargoAddStates.date_from))
    dp.message.register(process_date_to,     StateFilter(CargoAddStates.date_to))
    dp.callback_query.register(
        process_date_from_cb,
        StateFilter(CargoAddStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        process_date_to_cb,
        StateFilter(CargoAddStates.date_to),
        lambda c: c.data.startswith("cal:")
    )
    dp.message.register(process_weight,      StateFilter(CargoAddStates.weight))
    dp.message.register(process_body_type,   StateFilter(CargoAddStates.body_type))
    dp.message.register(process_is_local,    StateFilter(CargoAddStates.is_local))
    dp.message.register(process_comment,     StateFilter(CargoAddStates.comment))

    dp.message.register(cmd_start_find_cargo, lambda m: m.text == "🔍 Найти груз")
    dp.message.register(filter_city_from,     StateFilter(CargoSearchStates.city_from))
    dp.message.register(filter_city_to,       StateFilter(CargoSearchStates.city_to))
    dp.message.register(filter_date_from,     StateFilter(CargoSearchStates.date_from))
    dp.message.register(filter_date_to,       StateFilter(CargoSearchStates.date_to))
    dp.callback_query.register(
        filter_date_from_cb,
        StateFilter(CargoSearchStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        filter_date_to_cb,
        StateFilter(CargoSearchStates.date_to),
        lambda c: c.data.startswith("cal:")
    )
