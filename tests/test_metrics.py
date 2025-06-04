import os
import sys
import tempfile
import types

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

aiogram_module = types.ModuleType("aiogram")
aiogram_types_module = types.ModuleType("aiogram.types")
aiogram_module.types = aiogram_types_module
class _DummyMessage:
    pass
aiogram_types_module.Message = _DummyMessage
sys.modules.setdefault("aiogram", aiogram_module)
sys.modules.setdefault("aiogram.types", aiogram_types_module)

import sqlite3

import db
from metrics import get_bot_statistics


def setup_temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    monkeypatch.setattr(db, "DB_PATH", tmp.name)
    db.init_db()
    return tmp.name


def test_get_bot_statistics(monkeypatch):
    db_path = setup_temp_db(monkeypatch)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # user registered long ago
    cur.execute(
        "INSERT INTO users (telegram_id, name, city, phone, created_at) VALUES (1, 'old', 'c', 'p', '2020-01-01')"
    )
    # user registered now
    cur.execute(
        "INSERT INTO users (telegram_id, name, city, phone, created_at) VALUES (2, 'new', 'c', 'p', datetime('now'))"
    )
    conn.commit()
    conn.close()

    total, new = get_bot_statistics()
    assert total == 2
    assert new == 1
