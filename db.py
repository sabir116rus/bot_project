"""SQLite database helpers used by the bot."""

import sqlite3

from config import Config

# Database file path can be overridden in tests via monkeypatching
DB_PATH = Config.DB_PATH
# Always use path relative to this file so running the bot from any working
# directory works correctly. Path is now defined in Config.

def get_connection():
    """Return a new SQLite connection using :data:`DB_PATH`."""
    conn = sqlite3.connect(DB_PATH)
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
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS cargo (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        city_from TEXT,
        region_from TEXT,
        city_to TEXT,
        region_to TEXT,
        date_from TEXT,
        date_to TEXT,
        weight INTEGER CHECK(weight > 0 AND weight <= {Config.MAX_WEIGHT}),
        body_type TEXT,
        is_local INTEGER,
        comment TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS trucks (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        city TEXT,
        region TEXT,
        date_from TEXT,
        date_to TEXT,
        weight INTEGER CHECK(weight > 0 AND weight <= {Config.MAX_WEIGHT}),
        body_type TEXT,
        direction TEXT,  -- 'ищу заказ' / 'попутный'
        route_regions TEXT,  -- список регионов в текстовом виде
        comment TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    # Create indexes if they do not exist
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cargo_dates ON cargo(date_from, date_to)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cargo_cities ON cargo(city_from, city_to)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_trucks_city_date ON trucks(city, date_from)"
    )
    conn.commit()
    conn.close()


def get_cargo_by_user(user_id: int) -> list[sqlite3.Row]:
    """Return cargo entries owned by ``user_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, city_from, city_to, date_from, weight FROM cargo"
            " WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = cursor.fetchall()
    return rows


def get_trucks_by_user(user_id: int) -> list[sqlite3.Row]:
    """Return truck entries owned by ``user_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, city, date_from, weight FROM trucks"
            " WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = cursor.fetchall()
    return rows


if __name__ == "__main__":
    init_db()
    print("База данных инициализирована в", DB_PATH)
