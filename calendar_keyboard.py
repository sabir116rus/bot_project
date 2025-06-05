"""Inline calendar keyboard helpers."""

import calendar
from datetime import datetime

from aiogram import types
from aiogram.fsm.context import FSMContext

from db import get_connection
from handlers.common import get_main_menu, show_search_results
from utils import get_current_user_id, log_user_action


def generate_calendar(include_skip: bool = False) -> types.InlineKeyboardMarkup:
    """Return a simple calendar for the current month."""
    now = datetime.now()
    year, month = now.year, now.month
    cal = calendar.monthcalendar(year, month)

    rows: list[list[types.InlineKeyboardButton]] = []
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                row.append(
                    types.InlineKeyboardButton(text=str(day), callback_data=f"cal:{date_str}")
                )
        rows.append(row)

    if include_skip:
        rows.append([types.InlineKeyboardButton(text="Нет", callback_data="cal:skip")])

    return types.InlineKeyboardMarkup(inline_keyboard=rows)


async def handle_calendar_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Handle inline calendar selection for all scenarios."""

    value = "нет" if callback.data == "cal:skip" else callback.data.split(":", 1)[1]
    current_state = await state.get_state()

    await callback.message.delete()

    if current_state == "CargoAddStates:date_from":
        await state.update_data(date_from=value)
        bot = await callback.message.answer("Дата прибытия:", reply_markup=generate_calendar())
        await state.update_data(last_bot_message_id=bot.message_id, calendar_field="date_to")
        await state.set_state("CargoAddStates:date_to")
        await callback.answer()
        return

    if current_state == "CargoAddStates:date_to":
        data = await state.get_data()
        df = data.get("date_from")
        dt_from = datetime.strptime(df, "%Y-%m-%d") if df else None
        dt_to = datetime.strptime(value, "%Y-%m-%d")
        if dt_from and dt_to < dt_from:
            await callback.answer("Неверная дата", show_alert=True)
            return
        await state.update_data(date_to=value, calendar_field=None)
        bot = await callback.message.answer("Вес (в тоннах, цифрой):")
        await state.update_data(last_bot_message_id=bot.message_id)
        await state.set_state("CargoAddStates:weight")
        await callback.answer()
        return

    if current_state == "CargoSearchStates:date_from":
        key = "нет" if callback.data == "cal:skip" else value
        await state.update_data(filter_date_from=key)
        bot = await callback.message.answer(
            "Максимальная дата отправления:",
            reply_markup=generate_calendar(include_skip=True),
        )
        await state.update_data(last_bot_message_id=bot.message_id, calendar_field="filter_date_to")
        await state.set_state("CargoSearchStates:date_to")
        await callback.answer()
        return

    if current_state == "CargoSearchStates:date_to":
        key = "нет" if callback.data == "cal:skip" else value
        await state.update_data(filter_date_to=key, calendar_field=None)

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

        prev_bot = data.get("last_bot_message_id")
        if prev_bot:
            try:
                await callback.message.chat.delete_message(prev_bot)
            except Exception:
                pass

        if not rows:
            await callback.message.answer("📬 По вашему запросу ничего не найдено.", reply_markup=get_main_menu())
        else:
            await show_search_results(callback.message, rows)

        log_user_action(user_id, "cargo_search", f"results={len(rows)}")
        await state.clear()
        await callback.answer()
        return

    if current_state == "TruckAddStates:date_from":
        await state.update_data(date_from=value)
        bot = await callback.message.answer("Дата доступности (по):", reply_markup=generate_calendar())
        await state.update_data(last_bot_message_id=bot.message_id, calendar_field="date_to")
        await state.set_state("TruckAddStates:date_to")
        await callback.answer()
        return

    if current_state == "TruckAddStates:date_to":
        data = await state.get_data()
        df = data.get("date_from")
        dt_from = datetime.strptime(df, "%Y-%m-%d") if df else None
        dt_to = datetime.strptime(value, "%Y-%m-%d")
        if dt_from and dt_to < dt_from:
            await callback.answer("Неверная дата", show_alert=True)
            return
        await state.update_data(date_to=value, calendar_field=None)
        bot = await callback.message.answer("Грузоподъёмность (в тоннах):")
        await state.update_data(last_bot_message_id=bot.message_id)
        await state.set_state("TruckAddStates:weight")
        await callback.answer()
        return

    if current_state == "TruckSearchStates:date_from":
        key = "нет" if callback.data == "cal:skip" else value
        await state.update_data(filter_date_from=key)
        bot = await callback.message.answer(
            "Максимальная дата начала:",
            reply_markup=generate_calendar(include_skip=True),
        )
        await state.update_data(last_bot_message_id=bot.message_id, calendar_field="filter_date_to")
        await state.set_state("TruckSearchStates:date_to")
        await callback.answer()
        return

    if current_state == "TruckSearchStates:date_to":
        key = "нет" if callback.data == "cal:skip" else value
        await state.update_data(filter_date_to=key, calendar_field=None)

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

        prev_bot = data.get("last_bot_message_id")
        if prev_bot:
            try:
                await callback.message.chat.delete_message(prev_bot)
            except Exception:
                pass

        if not rows:
            await callback.message.answer("📬 По вашему запросу ТС не найдено.", reply_markup=get_main_menu())
        else:
            await show_search_results(callback.message, rows)

        log_user_action(user_id, "truck_search", f"results={len(rows)}")
        await state.clear()
        await callback.answer()
        return

    # Generic fallback for other cases
    data = await state.get_data()
    field = data.get("calendar_field")
    next_state = data.get("calendar_next_state")
    next_text = data.get("calendar_next_text")
    next_markup = data.get("calendar_next_markup")

    if field:
        await state.update_data(**{field: value})

    bot = await callback.message.answer(next_text, reply_markup=next_markup)
    await state.update_data(last_bot_message_id=bot.message_id)
    await state.set_state(next_state)
    await callback.answer()
