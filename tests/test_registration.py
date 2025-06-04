import os
import sys
import tempfile
import types
import sqlite3
import pytest
import asyncio

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# --- aiogram stubs -----------------------------------------------------------
aiogram_module = types.ModuleType("aiogram")
aiogram_types_module = types.ModuleType("aiogram.types")
aiogram_module.types = aiogram_types_module
aiogram_filters_module = types.ModuleType("aiogram.filters")
aiogram_module.filters = aiogram_filters_module
aiogram_fsm_context_module = types.ModuleType("aiogram.fsm.context")
aiogram_fsm_state_module = types.ModuleType("aiogram.fsm.state")
aiogram_module.fsm = types.ModuleType("aiogram.fsm")
aiogram_module.fsm.context = aiogram_fsm_context_module
aiogram_module.fsm.state = aiogram_fsm_state_module

class _DummyMessage:
    pass

class _DummyContentType:
    CONTACT = "contact"
    TEXT = "text"

aiogram_types_module.Message = _DummyMessage
aiogram_types_module.ContentType = _DummyContentType

class ReplyKeyboardRemove:
    pass

aiogram_types_module.ReplyKeyboardRemove = ReplyKeyboardRemove

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

class Command:
    def __init__(self, commands=None):
        self.commands = commands


class StateFilter:
    def __init__(self, state):
        self.state = state


aiogram_filters_module.Command = Command
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

sys.modules["aiogram"] = aiogram_module
sys.modules["aiogram.types"] = aiogram_types_module
sys.modules["aiogram.filters"] = aiogram_filters_module
sys.modules["aiogram.fsm.context"] = aiogram_fsm_context_module
sys.modules["aiogram.fsm.state"] = aiogram_fsm_state_module

# -----------------------------------------------------------------------------

handlers_pkg = types.ModuleType("handlers")
handlers_pkg.__path__ = []
sys.modules["handlers"] = handlers_pkg
common_stub = types.ModuleType("handlers.common")
common_stub.get_main_menu = lambda: None
sys.modules["handlers.common"] = common_stub

import importlib.util
import db
spec = importlib.util.spec_from_file_location("handlers.registration", os.path.join(os.path.dirname(__file__), "..", "handlers", "registration.py"))
registration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registration)


class DummyUser:
    def __init__(self, uid=1):
        self.id = uid


class DummyContact:
    def __init__(self, phone):
        self.phone_number = phone


class DummyMessage:
    def __init__(self, text=None, contact=None):
        self.text = text
        self.contact = contact
        self.deleted = False
        self.reply = None
        if contact:
            self.content_type = _DummyContentType.CONTACT
        else:
            self.content_type = _DummyContentType.TEXT
        self.from_user = DummyUser()

    async def delete(self):
        self.deleted = True

    async def answer(self, text, reply_markup=None):
        self.reply = text


class DummyFSMContext:
    def __init__(self, data=None):
        self._data = data or {}
        self.state = registration.Registration.phone

    async def get_data(self):
        return self._data

    async def clear(self):
        self.state = None
        self._data.clear()


def setup_temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    monkeypatch.setattr(db, "DB_PATH", tmp.name)
    db.init_db()
    return tmp.name


def test_process_phone_valid(monkeypatch):
    db_path = setup_temp_db(monkeypatch)
    monkeypatch.setattr(registration, "get_main_menu", lambda: None)
    monkeypatch.setattr(registration, "log_user_action", lambda *a, **kw: None)
    async def _get_uid(m):
        return 1
    monkeypatch.setattr(registration, "get_current_user_id", _get_uid)

    msg = DummyMessage(text="+79991234567")
    state = DummyFSMContext({"name": "N", "city": "C"})

    asyncio.run(registration.process_phone(msg, state))

    assert msg.deleted
    assert "Регистрация завершена" in msg.reply
    assert state.state is None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT phone FROM users WHERE telegram_id = 1").fetchone()
    conn.close()
    assert row["phone"] == "+79991234567"


def test_process_phone_invalid(monkeypatch):
    setup_temp_db(monkeypatch)
    monkeypatch.setattr(registration, "get_main_menu", lambda: None)
    monkeypatch.setattr(registration, "log_user_action", lambda *a, **kw: None)
    async def _get_uid_none(m):
        return None
    monkeypatch.setattr(registration, "get_current_user_id", _get_uid_none)

    msg = DummyMessage(text="12345")
    state = DummyFSMContext({"name": "N", "city": "C"})

    asyncio.run(registration.process_phone(msg, state))

    assert not msg.deleted
    assert "Некорректный номер" in msg.reply
    assert state.state == registration.Registration.phone
