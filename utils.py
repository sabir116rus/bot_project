# utils.py

from contextlib import contextmanager
from datetime import datetime

from aiogram import types
from db import get_connection


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
        dt = datetime.strptime(text.strip(), "%d.%m.%Y")
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
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return iso_date  # если парсинг не удался, возвращаем как есть
