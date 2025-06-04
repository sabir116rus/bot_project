"""Predefined regions and their cities for user selection."""

REGION_TO_CITIES: dict[str, list[str]] = {
    "Moscow Oblast": ["Moscow", "Khimki", "Podolsk"],
    "Saint Petersburg Oblast": ["Saint Petersburg", "Pushkin", "Pavlovsk"],
    "Novosibirsk Oblast": ["Novosibirsk", "Berdsk", "Iskitim"],
}


def get_regions() -> list[str]:
    """Return the list of available regions."""
    return list(REGION_TO_CITIES.keys())


def get_cities(region: str) -> list[str]:
    """Return the cities for the given region or empty list."""
    return REGION_TO_CITIES.get(region, [])
