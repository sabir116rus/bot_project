"""Finite state machine definitions for user interactions."""

from aiogram.fsm.state import State, StatesGroup


class BaseStates(StatesGroup):
    """Base class for FSM states with helper methods."""

    @classmethod
    def get_all_states(cls) -> list[State]:
        """Return all attributes that are instances of :class:`State`."""
        return [value for value in cls.__dict__.values() if isinstance(value, State)]


class CargoEditStates(BaseStates):
    """FSM states for cargo editing workflow."""

    weight = State()
    route_region_from = State()
    route_city_from = State()
    route_region_to = State()
    route_city_to = State()
    date_from = State()
    date_to = State()


class TruckEditStates(BaseStates):
    """FSM states for truck editing workflow."""

    weight = State()
    route_region = State()
    route_city = State()
    date_from = State()
    date_to = State()


class UserEditStates(BaseStates):
    """FSM states for editing user profile details."""

    name = State()
    city = State()
    phone = State()
