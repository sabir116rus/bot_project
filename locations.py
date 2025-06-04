"""Utilities for obtaining Russian regions and cities."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List

_DATA_FILE = os.path.join(os.path.dirname(__file__), "russia.json")


@lru_cache(maxsize=1)
def _load_mapping() -> dict[str, list[str]]:
    """Load region to city mapping from :data:`russia.json`."""
    with open(_DATA_FILE, "r", encoding="utf-8") as fh:
        records = json.load(fh)

    mapping: dict[str, list[str]] = {}
    for row in records:
        region = row["region"]
        city = row["city"]
        mapping.setdefault(region, []).append(city)

    for cities in mapping.values():
        cities.sort()
    return mapping


def get_regions() -> list[str]:
    """Return the full sorted list of regions."""
    mapping = _load_mapping()
    regions = sorted(mapping.keys())
    return regions


def get_cities(region: str) -> list[str]:
    """Return the full sorted list of cities for ``region``."""
    mapping = _load_mapping()
    return mapping.get(region, [])


