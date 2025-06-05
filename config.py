import os

class Config:
    """Application configuration constants."""
    # Database file path relative to this file
    DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.sqlite3")

    # Maximum weight allowed for cargo/truck entries (tons)
    MAX_WEIGHT = 1000

    # Date format used for user input/output
    DATE_FORMAT = "%d.%m.%Y"

    # Supported body types for vehicles/cargo
    BODY_TYPES = [
        "Рефрижератор",
        "Тент",
        "Изотерм",
    ]

    # Direction options for trucks
    TRUCK_DIRECTIONS = [
        "Ищу заказ",
        "Попутный путь",
    ]

    # Telegram IDs that have administrator rights
    ADMIN_IDS = [
        int(x)
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]
    