"""Utilities for obtaining Russian regions and cities."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List
from typing import Iterable, Tuple, List
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


def _paginate(items: Iterable[str], page: int, per_page: int) -> Tuple[List[str], bool, bool]:
    """Return a slice of ``items`` along with paging flags."""
    items = list(items)
    start = max(page, 0) * per_page
    end = start + per_page
    slice_ = items[start:end]
    has_prev = page > 0
    has_next = end < len(items)
    return slice_, has_prev, has_next


def get_regions_page(page: int = 0, per_page: int = 10) -> Tuple[List[str], bool, bool]:
    """Return a page of regions and navigation info."""
    return _paginate(get_regions(), page, per_page)


def get_cities_page(region: str, page: int = 0, per_page: int = 10) -> Tuple[List[str], bool, bool]:
    """Return a page of cities for ``region`` and navigation info."""
    return _paginate(get_cities(region), page, per_page)
