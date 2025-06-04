import os
import sys
import types
import asyncio
import importlib.util
import pytest

# Ensure project root on path
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

sys.modules.setdefault("aiogram", aiogram_module)
sys.modules.setdefault("aiogram.types", aiogram_types_module)
sys.modules.setdefault("aiogram.filters", aiogram_filters_module)
sys.modules.setdefault("aiogram.fsm.context", aiogram_fsm_context_module)
sys.modules.setdefault("aiogram.fsm.state", aiogram_fsm_state_module)

# -----------------------------------------------------------------------------

handlers_pkg = types.ModuleType("handlers")
handlers_pkg.__path__ = []
sys.modules["handlers"] = handlers_pkg

common_stub = types.ModuleType("handlers.common")
async def dummy_ask_and_store(*args, **kwargs):
    pass
async def dummy_show_search_results(*args, **kwargs):
    pass
common_stub.get_main_menu = lambda: None
common_stub.ask_and_store = dummy_ask_and_store
common_stub.show_search_results = dummy_show_search_results
common_stub.create_paged_keyboard = lambda *a, **k: None
sys.modules["handlers.common"] = common_stub

# Import cargo and truck modules manually
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
        self.chat = self

    async def answer(self, text, reply_markup=None):
        self.reply = text

    async def delete(self):
        pass

    async def delete_message(self, mid):
        pass


class DummyFSMContext:
    def __init__(self, state):
        self.state = state
        self.data = {}

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, st):
        self.state = st

    async def get_data(self):
        return self.data


async def fake_ask_and_store(message, state, text, next_state, reply_markup=None):
    message.stored = text
    await state.set_state(next_state)

async def fake_show_progress(message, state, step, total):
    message.progress = step


def test_cargo_process_weight_invalid(monkeypatch):
    monkeypatch.setattr(cargo, "ask_and_store", fake_ask_and_store)
    monkeypatch.setattr(cargo, "show_progress", fake_show_progress)

    called = {}
    def fake_validate(val):
        called["val"] = val
        return False, 0
    monkeypatch.setattr(cargo, "validate_weight", fake_validate)

    msg = DummyMessage("bad")
    state = DummyFSMContext(cargo.CargoAddStates.weight)
    asyncio.run(cargo.process_weight(msg, state))

    assert "введи" in msg.reply.lower()
    assert state.state == cargo.CargoAddStates.weight
    assert "stored" not in msg.__dict__
    assert called["val"] == "bad"


def test_cargo_process_weight_valid(monkeypatch):
    monkeypatch.setattr(cargo, "ask_and_store", fake_ask_and_store)
    monkeypatch.setattr(cargo, "show_progress", fake_show_progress)
    monkeypatch.setattr(cargo, "validate_weight", lambda v: (True, 5))

    msg = DummyMessage("5")
    state = DummyFSMContext(cargo.CargoAddStates.weight)
    asyncio.run(cargo.process_weight(msg, state))

    assert state.data["weight"] == 5
    assert state.state == cargo.CargoAddStates.body_type
    assert msg.stored.startswith("Выбери")


def test_truck_process_weight_invalid(monkeypatch):
    monkeypatch.setattr(truck, "ask_and_store", fake_ask_and_store)
    monkeypatch.setattr(truck, "show_progress", fake_show_progress)
    monkeypatch.setattr(truck, "validate_weight", lambda v: (False, 0))

    msg = DummyMessage("x")
    state = DummyFSMContext(truck.TruckAddStates.weight)
    asyncio.run(truck.process_weight(msg, state))

    assert "введи" in msg.reply.lower()
    assert state.state == truck.TruckAddStates.weight
    assert "stored" not in msg.__dict__


def test_truck_process_weight_valid(monkeypatch):
    monkeypatch.setattr(truck, "ask_and_store", fake_ask_and_store)
    monkeypatch.setattr(truck, "show_progress", fake_show_progress)
    monkeypatch.setattr(truck, "validate_weight", lambda v: (True, 8))

    msg = DummyMessage("8")
    state = DummyFSMContext(truck.TruckAddStates.weight)
    asyncio.run(truck.process_weight(msg, state))

    assert state.data["weight"] == 8
    assert state.state == truck.TruckAddStates.body_type
    assert msg.stored.startswith("Выбери")

