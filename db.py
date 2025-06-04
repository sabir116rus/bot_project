# db.py

import sqlite3

from config import Config

# Always use path relative to this file so running the bot from any working
# directory works correctly. Path is now defined in Config.

def get_connection():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        city TEXT,
        phone TEXT,
        created_at TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cargo (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        city_from TEXT,
        region_from TEXT,
        city_to TEXT,
        region_to TEXT,
        date_from TEXT,
        date_to TEXT,
        weight INTEGER,
        body_type TEXT,
        is_local INTEGER,
        comment TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trucks (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        city TEXT,
        region TEXT,
        date_from TEXT,
        date_to TEXT,
        weight INTEGER,
        body_type TEXT,
        direction TEXT,  -- 'ищу заказ' / 'попутный'
        route_regions TEXT,  -- список регионов в текстовом виде
        comment TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("База данных инициализирована в", Config.DB_PATH)
