import os
import sys
import tempfile
import types
import sqlite3
import asyncio

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Comprehensive aiogram stubs
aiogram_module = sys.modules.setdefault("aiogram", types.ModuleType("aiogram"))
aiogram_types_module = sys.modules.setdefault(
    "aiogram.types", types.ModuleType("aiogram.types")
)
aiogram_filters_module = sys.modules.setdefault(
    "aiogram.filters", types.ModuleType("aiogram.filters")
)
aiogram_fsm_context_module = sys.modules.setdefault(
    "aiogram.fsm.context", types.ModuleType("aiogram.fsm.context")
)
aiogram_fsm_state_module = sys.modules.setdefault(
    "aiogram.fsm.state", types.ModuleType("aiogram.fsm.state")
)
aiogram_module.types = aiogram_types_module
aiogram_module.filters = aiogram_filters_module
aiogram_module.fsm = sys.modules.setdefault("aiogram.fsm", types.ModuleType("aiogram.fsm"))
aiogram_module.fsm.context = aiogram_fsm_context_module
aiogram_module.fsm.state = aiogram_fsm_state_module

class _DummyMessage:
    pass

aiogram_types_module.Message = _DummyMessage

class KeyboardButton:
    def __init__(self, text=None, request_contact=None):
        self.text = text
        self.request_contact = request_contact

aiogram_types_module.KeyboardButton = KeyboardButton

class ReplyKeyboardMarkup:
    def __init__(self, *args, **kwargs):
        pass

aiogram_types_module.ReplyKeyboardMarkup = ReplyKeyboardMarkup

class InlineKeyboardButton:
    def __init__(self, text=None, callback_data=None):
        self.text = text
        self.callback_data = callback_data

aiogram_types_module.InlineKeyboardButton = InlineKeyboardButton

class InlineKeyboardMarkup:
    def __init__(self, *args, **kwargs):
        pass

aiogram_types_module.InlineKeyboardMarkup = InlineKeyboardMarkup

class CallbackQuery:
    def __init__(self, data=""):
        self.data = data
        self.message = DummyMessage()

    async def answer(self, *args, **kwargs):
        pass

aiogram_types_module.CallbackQuery = CallbackQuery

class StateFilter:
    def __init__(self, state):
        self.state = state

aiogram_filters_module.StateFilter = StateFilter

class FSMContext:
    pass

class State:
    pass

class StatesGroup:
    pass

aiogram_fsm_context_module.FSMContext = FSMContext
aiogram_fsm_state_module.State = State
aiogram_fsm_state_module.StatesGroup = StatesGroup

class Dispatcher:
    class _Message:
        def register(self, *args, **kwargs):
            pass

    def __init__(self):
        self.message = self._Message()

aiogram_module.Dispatcher = Dispatcher

handlers_pkg = types.ModuleType("handlers")
handlers_pkg.__path__ = []
sys.modules["handlers"] = handlers_pkg
common_stub = types.ModuleType("handlers.common")
common_stub.get_main_menu = lambda: None
sys.modules["handlers.common"] = common_stub

import db
import importlib.util

spec = importlib.util.spec_from_file_location(
    "handlers.profile",
    os.path.join(os.path.dirname(__file__), "..", "handlers", "profile.py"),
)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class DummyUser:
    def __init__(self, uid=1):
        self.id = uid


class DummyMessage:
    def __init__(self):
        self.from_user = DummyUser()
        self.reply = None

    async def answer(self, text, parse_mode=None, reply_markup=None):
        self.reply = text


def setup_temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    monkeypatch.setattr(db, "DB_PATH", tmp.name)
    db.init_db()
    return tmp.name


def test_show_profile_lists_entries(monkeypatch):
    db_path = setup_temp_db(monkeypatch)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (telegram_id, name, city, phone, created_at)"
        " VALUES (1, 'u', 'c', 'p', '2023-01-01')"
    )
    cur.execute(
        "INSERT INTO cargo (user_id, city_from, region_from, city_to, region_to,"
        " date_from, date_to, weight, body_type, is_local, comment, created_at)"
        " VALUES (1, 'A', 'AR', 'B', 'BR', '2024-01-01', '2024-01-02', 10,"
        " 'Тент', 0, '', '2023-01-01')"
    )
    cur.execute(
        "INSERT INTO trucks (user_id, city, region, date_from, date_to, weight,"
        " body_type, direction, route_regions, comment, created_at)"
        " VALUES (1, 'X', 'XR', '2024-01-01', '2024-01-02', 20, 'Тент',"
        " 'Ищу заказ', '', '', '2023-01-01')"
    )
    conn.commit()
    conn.close()

    msg = DummyMessage()
    asyncio.run(profile.show_profile(msg))

    assert "A → B" in msg.reply
    assert "X" in msg.reply

