# bot.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем регистраторы из всех модулей
from handlers import register_user_handlers, register_cargo_handlers, register_truck_handlers
from db import init_db

API_TOKEN = "7718441846:AAHo3_ESX8LvcTbVgZnGOpTdDc5Xzcfewt8"  # Твой реальный токен

async def main():
    logging.basicConfig(level=logging.INFO)

    # Инициализация БД (таблицы будут созданы, если их нет)
    init_db()

    # Создаём объекты Bot и Dispatcher
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем хендлеры
    register_user_handlers(dp)
    register_cargo_handlers(dp)
    register_truck_handlers(dp)

    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
