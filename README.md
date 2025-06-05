# bot_project

This Telegram bot allows users to register, add cargo and trucks, and search the database. It uses [aiogram](https://docs.aiogram.dev/) and stores data in a local SQLite database.

## Major features

- **User registration** via `/start` with name, city and phone number
  (11 digits, optionally starting with `+`).
- **Cargo management**: add new cargo entries and search existing ones.
- **Truck management**: add a truck and search available trucks.
- **Profile view** with "📋 Мой профиль" button.
- **Weight validation** ensures values are between 1 and 1000 tons.
- **Inline calendar** for selecting dates when adding or searching cargo and trucks.
- **Extensive region and city list** loaded from `russia.json`. When adding
  cargo or trucks the bot shows all regions and cities at once without paging.
- **Common commands** `/help` and `/cancel`.

## Running the bot

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy ``.env.example`` to ``.env`` and edit it with your credentials:

```bash
cp .env.example .env
# then open .env and set API_TOKEN and ADMIN_IDS
```

The bot reads ``API_TOKEN`` and ``ADMIN_IDS`` from this file automatically.

```
API_TOKEN=<your-telegram-token>
ADMIN_IDS=257928102,135255067
```

Alternatively you may export these variables in the shell before running
``bot.py``.

```bash
python bot.py
```

The SQLite database file is stored at `bot_database.sqlite3` in the project root (path defined in `Config.DB_PATH`).

## Available commands

- `/start` – begin registration or open the main menu.
- `/help` – show help message with available commands.
- `/cancel` – cancel the current operation and return to the main menu.
- `/admin` – open the admin panel (available for IDs listed in `ADMIN_IDS`).

The bot also provides buttons to add/search cargo or trucks and to view your profile.

## Running tests

Execute the test suite with `pytest` in the project root:

```bash
pytest
```

This uses the in-memory database and stub modules included in the tests.

