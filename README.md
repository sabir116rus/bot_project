# bot_project

This Telegram bot allows users to register, add cargo and trucks, and search the database. It uses [aiogram](https://docs.aiogram.dev/) and stores data in a local SQLite database.

## Major features

- **User registration** via `/start` with name, city and phone number
  (11 digits, optionally starting with `+`).
- **Cargo management**: add new cargo entries and search existing ones.
- **Truck management**: add a truck and search available trucks.
- **Profile view** with "📋 Мой профиль" button.
- **Progress bar** when filling long forms.
- **Weight validation** ensures values are between 1 and 1000 tons.
- **Inline calendar** for selecting dates when adding a truck.
- **Common commands** `/help` and `/cancel`.

## Running the bot

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Export your Telegram bot token as an environment variable and start the bot:

```bash
export API_TOKEN=<your-telegram-token>
python bot.py
```

`API_TOKEN` is required by `bot.py` to authenticate with Telegram.

The SQLite database file is stored at `bot_database.sqlite3` in the project root (path defined in `Config.DB_PATH`).

## Available commands

- `/start` – begin registration or open the main menu.
- `/help` – show help message with available commands.
- `/cancel` – cancel the current operation and return to the main menu.

The bot also provides buttons to add/search cargo or trucks and to view your profile.

## Running tests

Execute the test suite with `pytest` in the project root:

```bash
pytest
```

This uses the in-memory database and stub modules included in the tests.

