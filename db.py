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


def get_cargo(cargo_id: int) -> sqlite3.Row | None:
    """Return cargo entry by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM cargo WHERE id = ?",
            (cargo_id,),
        )
        row = cursor.fetchone()
    return row


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


def get_truck(truck_id: int) -> sqlite3.Row | None:
    """Return truck entry by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trucks WHERE id = ?", (truck_id,))
        row = cursor.fetchone()
    return row


def update_cargo_weight(cargo_id: int, weight: int) -> None:
    """Update ``weight`` for cargo entry with given ``cargo_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cargo SET weight = ? WHERE id = ?",
            (weight, cargo_id),
        )
        conn.commit()


def update_cargo_route(
    cargo_id: int,
    city_from: str,
    region_from: str,
    city_to: str,
    region_to: str,
) -> None:
    """Update route cities and regions for cargo entry ``cargo_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cargo SET city_from = ?, region_from = ?,"
            " city_to = ?, region_to = ? WHERE id = ?",
            (city_from, region_from, city_to, region_to, cargo_id),
        )
        conn.commit()


def update_cargo_dates(cargo_id: int, date_from: str, date_to: str) -> None:
    """Update dates for cargo entry ``cargo_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE cargo SET date_from = ?, date_to = ? WHERE id = ?",
            (date_from, date_to, cargo_id),
        )
        conn.commit()


def delete_cargo(cargo_id: int) -> None:
    """Remove cargo entry identified by ``cargo_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cargo WHERE id = ?", (cargo_id,))
        conn.commit()


def update_truck_weight(truck_id: int, weight: int) -> None:
    """Update ``weight`` for truck entry with given ``truck_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trucks SET weight = ? WHERE id = ?",
            (weight, truck_id),
        )
        conn.commit()


def update_truck_route(truck_id: int, city: str, region: str) -> None:
    """Update location city and region for truck entry ``truck_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trucks SET city = ?, region = ? WHERE id = ?",
            (city, region, truck_id),
        )
        conn.commit()


def update_truck_dates(truck_id: int, date_from: str, date_to: str) -> None:
    """Update dates for truck entry ``truck_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trucks SET date_from = ?, date_to = ? WHERE id = ?",
            (date_from, date_to, truck_id),
        )
        conn.commit()


def delete_truck(truck_id: int) -> None:
    """Remove truck entry identified by ``truck_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trucks WHERE id = ?", (truck_id,))
        conn.commit()


def update_user_name(user_id: int, name: str) -> None:
    """Update ``name`` for user with ``user_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        conn.commit()


def update_user_city(user_id: int, city: str) -> None:
    """Update ``city`` for user with ``user_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET city = ? WHERE id = ?", (city, user_id))
        conn.commit()


def update_user_phone(user_id: int, phone: str) -> None:
    """Update ``phone`` for user with ``user_id``."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone = ? WHERE id = ?", (phone, user_id))
        conn.commit()


def delete_user(user_id: int) -> None:
    """Remove user and associated cargo and trucks."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cargo WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM trucks WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()


if __name__ == "__main__":
    init_db()
    print("База данных инициализирована в", DB_PATH)
