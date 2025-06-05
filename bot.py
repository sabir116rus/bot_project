"""Telegram bot entry point and handler registration."""

import asyncio
import logging
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Регистрируем новые хендлеры
from handlers import (
    register_user_handlers,
    register_cargo_handlers,
    register_truck_handlers,
    register_profile_handler,
    register_common_handlers,
    register_admin_handlers,
)

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

async def main():
    try:
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO)

        # Инициализация БД
        from db import init_db
        init_db()

        # Логируем базовую статистику
        from metrics import get_bot_statistics
        total_users, new_users = get_bot_statistics()
        logging.info(
            "Bot stats: total_users=%s, registered_last_24h=%s",
            total_users,
            new_users,
        )

        # Создаём бота и диспетчер
        bot = Bot(token=API_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        # Регистрируем хендлеры
        register_user_handlers(dp)
        register_cargo_handlers(dp)
        register_truck_handlers(dp)
        register_profile_handler(dp)
        register_common_handlers(dp)
        register_admin_handlers(dp)

        # Запускаем поллинг
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
