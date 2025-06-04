import os
import sys
import types
import pytest

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Provide a minimal stub for the aiogram.types module so that utils can be
# imported without installing the real dependency.
aiogram_module = types.ModuleType("aiogram")
aiogram_types_module = types.ModuleType("aiogram.types")
aiogram_module.types = aiogram_types_module
class _DummyMessage:
    pass
aiogram_types_module.Message = _DummyMessage
sys.modules.setdefault("aiogram", aiogram_module)
sys.modules.setdefault("aiogram.types", aiogram_types_module)

from utils import parse_date, format_date_for_display


def test_parse_date_valid():
    assert parse_date("12.08.2023") == "2023-08-12"


def test_parse_date_invalid():
    assert parse_date("31.02.2023") is None
    assert parse_date("invalid") is None


def test_format_date_for_display_date_only():
    assert format_date_for_display("2023-08-12") == "12.08.2023"


def test_format_date_for_display_with_time():
    assert format_date_for_display("2023-08-12T13:45:00") == "12.08.2023"


def test_format_date_for_display_invalid():
    assert format_date_for_display("oops") == "oops"
