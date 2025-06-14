"""Aggregate registration functions for all bot handlers."""

from .registration import register_user_handlers
from .cargo import register_cargo_handlers
from .truck import register_truck_handlers
from .profile import register_profile_handler
from .common import register_common_handlers
from .admin import register_admin_handlers
