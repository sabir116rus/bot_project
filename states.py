from aiogram.fsm.state import State, StatesGroup


class BaseStates(StatesGroup):
    """Base class for FSM states with helper methods."""

    @classmethod
    def get_all_states(cls) -> list[State]:
        """Return all attributes that are instances of :class:`State`."""
        return [value for value in cls.__dict__.values() if isinstance(value, State)]
