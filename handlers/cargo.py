"""Handlers related to cargo addition and search workflows."""

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
    process_weight_step,
    parse_and_store_date,
)

from calendar_keyboard import generate_calendar, handle_calendar_callback
from utils import (
    get_current_user_id,
    format_date_for_display,
    log_user_action,
    get_unique_cities_from,
    get_unique_cities_to,
    clear_city_cache,
    validate_weight,
)
from locations import (
    get_regions,
    get_cities,
)


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

    # Сразу показываем все регионы (без пагинации)
    regions = get_regions()
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=region)] for region in regions],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await ask_and_store(
        message,
        state,
        "📦 Начнём добавление груза.\nВыбери регион отправления:",
        CargoAddStates.region_from,
        reply_markup=kb,
    )


async def process_region_from(message: types.Message, state: FSMContext):
    text = message.text.strip()
    all_regions = get_regions()
    if text not in all_regions:
        await message.answer("Пожалуйста, выбери регион из списка.")
        return

    await state.update_data(region_from=text)
    # Показываем все города выбранного региона
    cities = get_cities(text)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=city)] for city in cities],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await ask_and_store(
        message,
        state,
        "Откуда (город):",
        CargoAddStates.city_from,
        reply_markup=kb,
    )


async def process_city_from(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    region = data.get("region_from")
    if not region:
        # На всякий случай, если state потерялся
        await message.answer("Попробуйте снова: выберите регион отправления.")
        await state.clear()
        return

    cities = get_cities(region)
    if text not in cities:
        await message.answer("Пожалуйста, выбери город из списка.")
        return

    await state.update_data(city_from=text)

    # Теперь выбираем регион назначения (опять же, весь список)
    regions = get_regions()
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=region)] for region in regions],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await ask_and_store(
        message,
        state,
        "Регион назначения:",
        CargoAddStates.region_to,
        reply_markup=kb,
    )


async def process_region_to(message: types.Message, state: FSMContext):
    text = message.text.strip()
    all_regions = get_regions()
    if text not in all_regions:
        await message.answer("Пожалуйста, выбери регион из списка.")
        return

    await state.update_data(region_to=text)
    # Показываем все города выбранного региона назначения
    cities = get_cities(text)
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=city)] for city in cities],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await ask_and_store(
        message,
        state,
        "Куда (город):",
        CargoAddStates.city_to,
        reply_markup=kb,
    )


async def process_city_to(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    region = data.get("region_to")
    if not region:
        await message.answer("Попробуйте снова: выберите регион назначения.")
        await state.clear()
        return

    cities = get_cities(region)
    if text not in cities:
        await message.answer("Пожалуйста, выбери город из списка.")
        return

    await state.update_data(city_to=text)
    # Переходим к выбору даты отправления через календарь
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
        calendar_include_skip=False,
    )


async def process_date_to(message: types.Message, state: FSMContext):
    ok = await parse_and_store_date(
        message,
        state,
        "date_to",
        "Неверный формат даты. Введите ДД.MM.ГГГГ:",
        compare_field="date_from",
        compare_error="Дата прибытия не может быть раньше даты отправления. Повторите ввод:",
    )
    if not ok:
        return

    await ask_and_store(
        message,
        state,
        "Вес (в тоннах, цифрой):",
        CargoAddStates.weight
    )
    await state.update_data(calendar_field=None)

async def process_weight(message: types.Message, state: FSMContext):
    """Store cargo weight after validating the user input."""
    await process_weight_step(
        message,
        state,
        CargoAddStates.body_type,
        "Выбери тип кузова:",
        "Не важно",
        "Пожалуйста, введи вес от 1 до 1000 тонн цифрой (например, 12):",
        validate_func=validate_weight,
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
        calendar_include_skip=True,
    )
    await state.set_state(CargoSearchStates.date_from)


async def filter_date_from(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        ok = await parse_and_store_date(
            message,
            state,
            "filter_date_from",
            "Неверный формат даты. Введите ДД.MM.ГГГГ или «нет».",
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
        calendar_include_skip=True,
    )
    await state.set_state(CargoSearchStates.date_to)


async def filter_date_to(message: types.Message, state: FSMContext):
    raw = message.text.strip().lower()
    if raw != "нет":
        ok = await parse_and_store_date(
            message,
            state,
            "filter_date_to",
            "Неверный формат даты. Введите ДД.MM.ГГГГ или «нет».",
        )
        if not ok:
            return
    else:
        await state.update_data(filter_date_to="нет")

    data = await state.get_data()
    user_id = await get_current_user_id(message)
    fc_from = data.get("filter_city_from", "")
    fc_to = data.get("filter_city_to", "")
    fd_from = data.get("filter_date_from", "")
    fd_to = data.get("filter_date_to", "")

    base_query = """
    SELECT c.id, u.name, c.city_from, c.region_from, c.city_to, c.region_to, c.date_from, c.weight, c.body_type
    FROM cargo c
    JOIN users u ON c.user_id = u.id
    WHERE 1=1
    """
    filters = [
        (fc_from if fc_from != "все" else None, " AND lower(c.city_from) = ?"),
        (fc_to if fc_to != "все" else None, " AND lower(c.city_to) = ?"),
        (fd_from if fd_from != "нет" else None, " AND date(c.date_from) >= date(?)"),
        (fd_to if fd_to != "нет" else None, " AND date(c.date_from) <= date(?)"),
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
        await message.answer("📬 По вашему запросу ничего не найдено.", reply_markup=get_main_menu())
    else:
        await show_search_results(message, rows)

    log_user_action(user_id, "cargo_search", f"results={len(rows)}")
    await state.clear()




def register_cargo_handlers(dp: Dispatcher):
    # Добавление груза
    dp.message.register(cmd_start_add_cargo, lambda m: m.text == "➕ Добавить груз")
    dp.message.register(process_region_from, StateFilter(CargoAddStates.region_from))
    dp.message.register(process_city_from,   StateFilter(CargoAddStates.city_from))
    dp.message.register(process_region_to,   StateFilter(CargoAddStates.region_to))
    dp.message.register(process_city_to,     StateFilter(CargoAddStates.city_to))
    dp.message.register(process_date_from,   StateFilter(CargoAddStates.date_from))
    dp.message.register(process_date_to,     StateFilter(CargoAddStates.date_to))
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(CargoAddStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(CargoAddStates.date_to),
        lambda c: c.data.startswith("cal:")
    )
    dp.message.register(process_weight,      StateFilter(CargoAddStates.weight))
    dp.message.register(process_body_type,   StateFilter(CargoAddStates.body_type))
    dp.message.register(process_is_local,    StateFilter(CargoAddStates.is_local))
    dp.message.register(process_comment,     StateFilter(CargoAddStates.comment))

    # Поиск груза
    dp.message.register(cmd_start_find_cargo, lambda m: m.text == "🔍 Найти груз")
    dp.message.register(filter_city_from,     StateFilter(CargoSearchStates.city_from))
    dp.message.register(filter_city_to,       StateFilter(CargoSearchStates.city_to))
    dp.message.register(filter_date_from,     StateFilter(CargoSearchStates.date_from))
    dp.message.register(filter_date_to,       StateFilter(CargoSearchStates.date_to))
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(CargoSearchStates.date_from),
        lambda c: c.data.startswith("cal:")
    )
    dp.callback_query.register(
        handle_calendar_callback,
        StateFilter(CargoSearchStates.date_to),
        lambda c: c.data.startswith("cal:")
    )
