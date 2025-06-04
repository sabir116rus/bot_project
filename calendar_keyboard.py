"""Inline calendar keyboard helpers."""

from datetime import datetime
import calendar
from aiogram import types


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


async def handle_calendar_callback(callback: types.CallbackQuery, state) -> None:
    """Process calendar callbacks and ask next question."""
    data = await state.get_data()
    field = data.get("calendar_field")
    next_state = data.get("calendar_next_state")
    next_text = data.get("calendar_next_text")
    next_markup = data.get("calendar_next_markup")

    if callback.data == "cal:skip":
        value = "нет"
    else:
        value = callback.data.split(":", 1)[1]

    if field:
        await state.update_data(**{field: value})

    await callback.message.delete()
    bot_msg = await callback.message.answer(next_text, reply_markup=next_markup)
    await state.update_data(last_bot_message_id=bot_msg.message_id)
    await state.set_state(next_state)
    await callback.answer()
