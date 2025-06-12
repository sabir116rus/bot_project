import os
import sys
import types
import sqlite3
import asyncio
import tempfile

# Ensure project root on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# aiogram stubs
aiogram_module = types.ModuleType("aiogram")
aiogram_types = types.ModuleType("aiogram.types")
aiogram_filters = types.ModuleType("aiogram.filters")
aiogram_fsm_context = types.ModuleType("aiogram.fsm.context")
aiogram_fsm_state = types.ModuleType("aiogram.fsm.state")
aiogram_module.types = aiogram_types
aiogram_fsm = types.ModuleType("aiogram.fsm")
aiogram_fsm.context = aiogram_fsm_context
aiogram_fsm.state = aiogram_fsm_state
aiogram_module.fsm = aiogram_fsm
sys.modules.setdefault("aiogram", aiogram_module)
sys.modules.setdefault("aiogram.types", aiogram_types)
sys.modules.setdefault("aiogram.filters", aiogram_filters)
sys.modules.setdefault("aiogram.fsm.context", aiogram_fsm_context)
sys.modules.setdefault("aiogram.fsm.state", aiogram_fsm_state)

class _DummyMessage:
    pass

aiogram_types.Message = _DummyMessage

class KeyboardButton:
    def __init__(self, text=None, request_contact=None):
        self.text = text
        self.request_contact = request_contact

aiogram_types.KeyboardButton = KeyboardButton

class InlineKeyboardButton:
    def __init__(self, text=None, callback_data=None):
        self.text = text
        self.callback_data = callback_data

aiogram_types.InlineKeyboardButton = InlineKeyboardButton

class InlineKeyboardMarkup:
    def __init__(self, inline_keyboard=None):
        self.inline_keyboard = inline_keyboard

aiogram_types.InlineKeyboardMarkup = InlineKeyboardMarkup

class ReplyKeyboardMarkup:
    def __init__(self, *args, **kwargs):
        pass

aiogram_types.ReplyKeyboardMarkup = ReplyKeyboardMarkup
aiogram_fsm.InlineKeyboardMarkup = InlineKeyboardMarkup

class CallbackQuery:
    def __init__(self, data=""):
        self.data = data
        self.message = DummyMessage()
        self.answered = None

    async def answer(self, text=None):
        self.answered = text

aiogram_types.CallbackQuery = CallbackQuery

class StateFilter:
    def __init__(self, state):
        self.state = state

aiogram_filters.StateFilter = StateFilter

class FSMContext:
    pass

aiogram_fsm_context.FSMContext = FSMContext

class State:
    pass

class StatesGroup:
    pass

aiogram_fsm_state.State = State
aiogram_fsm_state.StatesGroup = StatesGroup

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
common_stub.ask_and_store = lambda *a, **k: None
common_stub.show_search_results = lambda *a, **k: None
common_stub.create_paged_keyboard = lambda *a, **k: None
common_stub.process_weight_step = lambda *a, **k: None
common_stub.parse_and_store_date = lambda *a, **k: True
sys.modules["handlers.common"] = common_stub

import importlib.util
import db

spec = importlib.util.spec_from_file_location(
    "handlers.cargo",
    os.path.join(os.path.dirname(__file__), "..", "handlers", "cargo.py"),
)
cargo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cargo)

spec = importlib.util.spec_from_file_location(
    "handlers.truck",
    os.path.join(os.path.dirname(__file__), "..", "handlers", "truck.py"),
)
truck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(truck)

class DummyMessage:
    def __init__(self, text=""):
        self.text = text
        self.reply = None
        self.markup = None
        self.chat = self
        self.from_user = type("U", (), {"id": 1})()

    async def answer(self, text, reply_markup=None):
        self.reply = text
        self.markup = reply_markup

    async def delete(self):
        pass

    async def delete_message(self, mid):
        pass

class DummyCallbackQuery:
    def __init__(self, data=""):
        self.data = data
        self.message = DummyMessage()
        self.answered = None

    async def answer(self, text=None):
        self.answered = text

class DummyFSM:
    def __init__(self):
        self.state = None
        self.data = {}

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, st):
        self.state = st

    async def get_data(self):
        return self.data

    async def clear(self):
        self.state = None
        self.data.clear()

def setup_temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    monkeypatch.setattr(db, "DB_PATH", tmp.name)
    db.init_db()
    return tmp.name


def test_edit_and_delete_flows(monkeypatch):
    db_path = setup_temp_db(monkeypatch)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (telegram_id, name, city, phone, created_at) VALUES (1, 'u', 'c', 'p', '2020-01-01')"
    )
    cur.execute(
        "INSERT INTO cargo (user_id, city_from, region_from, city_to, region_to, date_from, date_to, weight, body_type, is_local, comment, created_at) VALUES (1, 'A', 'AR', 'B', 'BR', '2024-01-01', '2024-01-02', 10, 'Тент', 0, '', '2023-01-01')"
    )
    cur.execute(
        "INSERT INTO trucks (user_id, city, region, date_from, date_to, weight, body_type, direction, route_regions, comment, created_at) VALUES (1, 'X', 'XR', '2024-01-01', '2024-01-02', 20, 'Тент', 'Ищу заказ', '', '', '2023-01-01')"
    )
    conn.commit()
    conn.close()

    state = DummyFSM()
    cq = DummyCallbackQuery("edit_cargo_weight:1")
    asyncio.run(cargo.start_edit_cargo_weight(cq, state))
    assert state.state == cargo.CargoEditStates.weight
    msg = DummyMessage("55")
    asyncio.run(cargo.process_edit_weight(msg, state))
    conn = sqlite3.connect(db_path)
    new_w = conn.execute("SELECT weight FROM cargo WHERE id=1").fetchone()[0]
    conn.close()
    assert new_w == 55
    assert state.state is None

    state = DummyFSM()
    cq = DummyCallbackQuery("edit_cargo_route:1")
    asyncio.run(cargo.start_edit_cargo_route(cq, state))
    assert state.state == cargo.CargoEditStates.route_from
    asyncio.run(cargo.process_edit_route_from(DummyMessage("X"), state))
    assert state.state == cargo.CargoEditStates.route_to
    asyncio.run(cargo.process_edit_route_to(DummyMessage("Y"), state))
    conn = sqlite3.connect(db_path)
    r = conn.execute("SELECT city_from, city_to FROM cargo WHERE id=1").fetchone()
    conn.close()
    assert r == ("X", "Y")

    state = DummyFSM()
    cq = DummyCallbackQuery("edit_truck_route:1")
    asyncio.run(truck.start_edit_truck_route(cq, state))
    assert state.state == truck.TruckEditStates.route
    asyncio.run(truck.process_edit_truck_route(DummyMessage("R"), state))
    conn = sqlite3.connect(db_path)
    route = conn.execute("SELECT route_regions FROM trucks WHERE id=1").fetchone()[0]
    conn.close()
    assert route == "R"

    state = DummyFSM()
    cq = DummyCallbackQuery("edit_truck_dates:1")
    asyncio.run(truck.start_edit_truck_dates(cq, state))
    assert state.state == truck.TruckEditStates.date_from
    asyncio.run(truck.process_edit_truck_date_from(DummyMessage("2030-01-01"), state))
    assert state.state == truck.TruckEditStates.date_to
    asyncio.run(truck.process_edit_truck_date_to(DummyMessage("2030-01-02"), state))
    conn = sqlite3.connect(db_path)
    df, dt = conn.execute("SELECT date_from, date_to FROM trucks WHERE id=1").fetchone()
    conn.close()
    assert df == "2030-01-01" and dt == "2030-01-02"

    state = DummyFSM()
    cq = DummyCallbackQuery("del_truck:1")
    asyncio.run(truck.handle_delete_truck(cq))
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM trucks").fetchone()[0]
    conn.close()
    assert count == 0


def test_edit_profile(monkeypatch):
    db_path = setup_temp_db(monkeypatch)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (telegram_id, name, city, phone, created_at) VALUES (1, 'u', 'c', 'p', '2020-01-01')"
    )
    conn.commit()
    conn.close()

    state = DummyFSM()
    spec = importlib.util.spec_from_file_location(
        "handlers.profile",
        os.path.join(os.path.dirname(__file__), "..", "handlers", "profile.py"),
    )
    profile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profile)

    cq = DummyCallbackQuery("edit_name")
    asyncio.run(profile.start_edit_name(cq, state))
    assert state.state == profile.UserEditStates.name
    msg = DummyMessage("new")
    asyncio.run(profile.process_new_name(msg, state))
    conn = sqlite3.connect(db_path)
    name = conn.execute("SELECT name FROM users WHERE telegram_id=1").fetchone()[0]
    conn.close()
    assert name == "new"
