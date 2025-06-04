# handlers/cargo.py

from aiogram import types, Dispatcher
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from states import BaseStates
from datetime import datetime

from db import get_connection
from .common import get_main_menu, ask_and_store
from utils import parse_date, get_current_user_id, format_date_for_display


class CargoAddStates(BaseStates):
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
    await message.answer("📦 Начнём добавление груза.\nОткуда (город):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CargoAddStates.city_from)


async def process_city_from(message: types.Message, state: FSMContext):
    await state.update_data(city_from=message.text.strip())

    await ask_and_store(
        message,
        state,
        "Регион отправления:",
        CargoAddStates.region_from
    )


async def process_region_from(message: types.Message, state: FSMContext):
    await state.update_data(region_from=message.text.strip())
    await ask_and_store(
        message,
        state,
        "Куда (город):",
        CargoAddStates.city_to
    )


async def process_city_to(message: types.Message, state: FSMContext):
    await state.update_data(city_to=message.text.strip())
    await ask_and_store(
        message,
        state,
        "Регион назначения:",
        CargoAddStates.region_to
    )


async def process_region_to(message: types.Message, state: FSMContext):
    await state.update_data(region_to=message.text.strip())
    await ask_and_store(
        message,
        state,
        "Дата отправления (ДД.MM.ГГГГ):",
        CargoAddStates.date_from
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
        "Дата прибытия (ДД.MM.ГГГГ):",
        CargoAddStates.date_to
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
    await ask_and_store(
        message,
        state,
        "Вес (в тоннах, цифрой):",
        CargoAddStates.weight
    )


async def process_weight(message: types.Message, state: FSMContext):
    raw = message.text.strip()
    try:
        weight = int(raw)
    except ValueError:
        await message.answer("Пожалуйста, введи вес цифрой (например, 12):")
        return

    await state.update_data(weight=weight)

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
    await ask_and_store(
        message,
        state,
        "Выбери тип кузова:",
        CargoAddStates.body_type,
        reply_markup=kb
    )


async def process_body_type(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text not in ("Рефрижератор", "Тент", "Изотерм", "Не важно"):
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

    await message.answer("✅ Груз успешно добавлен!", reply_markup=get_main_menu())
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

    # Получаем список уникальных городов отправления из таблицы cargo
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT city_from FROM cargo WHERE city_from IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    cities = [r["city_from"] for r in rows if r["city_from"].strip()]
    cities.sort(key=lambda x: x.lower())  # отсортируем по алфавиту

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

    # Теперь предлагаем выбрать город назначения аналогично
    # Получаем уникальные города назначения из cargo
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT city_to FROM cargo WHERE city_to IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    to_cities = [r["city_to"] for r in rows if r["city_to"].strip()]
    to_cities.sort(key=lambda x: x.lower())

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
        "Введите минимальную дату отправления (ДД.MM.ГГГГ) или «нет»:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
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
        "Введите максимальную дату отправления (ДД.MM.ГГГГ) или «нет»:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(last_bot_message_id=bot_msg.message_id)
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
        text = "📋 Найденные грузы:\n\n"
        for r in rows:
            date_disp = format_date_for_display(r["date_from"])
            text += (
                f"ID: {r['id']}\n"
                f"Владелец: {r['name']}\n"
                f"{r['city_from']}, {r['region_from']} → {r['city_to']}, {r['region_to']}\n"
                f"Дата отправления: {date_disp}\n"
                f"Вес: {r['weight']} т, Кузов: {r['body_type']}\n\n"
            )
        await message.answer(text, reply_markup=get_main_menu())

    await state.clear()

def register_cargo_handlers(dp: Dispatcher):
    # Добавление груза (осталось без изменений)
    dp.message.register(cmd_start_add_cargo, lambda m: m.text == "➕ Добавить груз")
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

    dp.message.register(cmd_start_find_cargo, lambda m: m.text == "🔍 Найти груз")
    dp.message.register(filter_city_from,     StateFilter(CargoSearchStates.city_from))
    dp.message.register(filter_city_to,       StateFilter(CargoSearchStates.city_to))
    dp.message.register(filter_date_from,     StateFilter(CargoSearchStates.date_from))
    dp.message.register(filter_date_to,       StateFilter(CargoSearchStates.date_to))
