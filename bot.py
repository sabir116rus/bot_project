# bot.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers.registration import register_user_handlers
from db import init_db

API_TOKEN = "7718441846:AAHo3_ESX8LvcTbVgZnGOpTdDc5Xzcfewt8"  # <-- Замените на реальный токен вашего бота


async def main():
    # Логирование
    logging.basicConfig(level=logging.INFO)

    # Инициализация БД (создание таблиц)
    init_db()

    # Создаём объекты Bot и Dispatcher с памятью для FSM
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем хендлеры (модуль registration.py)
    register_user_handlers(dp)

    # Стартуем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
