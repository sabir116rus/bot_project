# bot.py

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
    register_profile_handler
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

        # Создаём бота и диспетчер
        bot = Bot(token=API_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        # Регистрируем хендлеры
        register_user_handlers(dp)
        register_cargo_handlers(dp)
        register_truck_handlers(dp)
        register_profile_handler(dp)

        # Запускаем поллинг
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
