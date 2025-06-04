# utils.py

from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache

import logging
import re
from aiogram import types
from aiogram.fsm.context import FSMContext
from db import get_connection
from config import Config


@contextmanager
def db_cursor():
    """
    Контекстный менеджер для работы с БД через sqlite3.
    Пример использования:
        with db_cursor() as cursor:
            cursor.execute(...)
            ...
    В конце автоматически выполняется conn.commit() и conn.close().
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    finally:
        conn.close()


def parse_date(text: str) -> str | None:
    """
    Пытается разобрать дату из формата 'ДД.MM.ГГГГ'.
    Если успешно, возвращает строку 'ГГГГ-ММ-ДД' (для хранения в БД).
    Если не удалось — возвращает None.
    """
    try:
        dt = datetime.strptime(text.strip(), Config.DATE_FORMAT)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


async def get_current_user_id(message: types.Message) -> int | None:
    """
    Возвращает id пользователя из таблицы users по telegram_id.
    Если пользователь не найден — возвращает None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else None


def format_date_for_display(iso_date: str) -> str:
    """
    Принимает строку в формате 'ГГГГ-ММ-ДД' или 'ГГГГ-ММ-ДДT...' и
    возвращает 'ДД.MM.ГГГГ'. 
    """
    try:
        # Если приходит формат 'YYYY-MM-DDTHH:MM:SS...', берём первые 10 символов
        date_part = iso_date.split("T")[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime(Config.DATE_FORMAT)
    except Exception:
        return iso_date  # если парсинг не удался, возвращаем как есть



async def show_progress(
    message: types.Message,
    state: FSMContext,
    step: int,
    total: int,
) -> None:
    """Send a progress bar and store its message id in ``state``."""
    if total <= 0:
        return

    bar_length = 10
    filled = int(bar_length * step / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    bot_msg = await message.answer(f"Прогресс: {bar} {step}/{total}")
    await state.update_data(last_progress_message_id=bot_msg.message_id)

# ==== Cached helpers for unique cities ====

@lru_cache(maxsize=1)
def get_unique_cities_from() -> list[str]:
    """Return sorted list of unique origin cities from cargo table."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT city_from FROM cargo WHERE city_from IS NOT NULL"
        )
        rows = cursor.fetchall()

    cities = [r["city_from"] for r in rows if r["city_from"].strip()]
    cities.sort(key=lambda x: x.lower())
    return cities


@lru_cache(maxsize=1)
def get_unique_cities_to() -> list[str]:
    """Return sorted list of unique destination cities from cargo table."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT city_to FROM cargo WHERE city_to IS NOT NULL"
        )
        rows = cursor.fetchall()

    cities = [r["city_to"] for r in rows if r["city_to"].strip()]
    cities.sort(key=lambda x: x.lower())
    return cities


@lru_cache(maxsize=1)
def get_unique_truck_cities() -> list[str]:
    """Return sorted list of unique truck cities from trucks table."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT city FROM trucks WHERE city IS NOT NULL"
        )
        rows = cursor.fetchall()

    cities = [r["city"] for r in rows if r["city"].strip()]
    cities.sort(key=lambda x: x.lower())
    return cities


def clear_city_cache() -> None:
    """Invalidate cached city lists."""
    get_unique_cities_from.cache_clear()
    get_unique_cities_to.cache_clear()
    get_unique_truck_cities.cache_clear()

def log_user_action(user_id: int, action: str, details: str = "") -> None:
    """Log a user action for auditing purposes."""
    if details:
        logging.info("user=%s action=%s details=%s", user_id, action, details)
    else:
        logging.info("user=%s action=%s", user_id, action)

def validate_weight(weight_str: str) -> tuple[bool, int]:
    """Validate and convert weight string to integer tons.

    The weight must be a positive integer between 1 and 1000 (tons).
    Returns a tuple ``(is_valid, value)`` where ``value`` is 0 when invalid.
    """
    try:
        weight = int(weight_str.strip())
    except (TypeError, ValueError):
        return False, 0
    if 1 <= weight <= 1000:
        return True, weight
    return False, 0


_PHONE_RE = re.compile(r"^\+?\d{11}$")


def validate_phone(phone: str) -> bool:
    """Return ``True`` if the phone number matches ``+?\d{11}``."""
    return bool(_PHONE_RE.fullmatch(phone.strip()))
