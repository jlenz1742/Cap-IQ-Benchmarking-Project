"""Free-text location lookup via the OpenStreetMap Nominatim API.

Used only for ``--location "10115 Berlin"``-style single-point searches so a
postal code or city name can be turned into coordinates. Nominatim's usage
policy (https://operations.osmfoundation.org/policies/nominatim/) caps
requests at 1/second and requires a descriptive User-Agent identifying the
application (and ideally contact info) -- callers should pass their own
``user_agent`` rather than relying on the generic default.
"""

from __future__ import annotations

from typing import Optional, Tuple

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_USER_AGENT = "bosch-dealers-scraper/1.0 (contact: set --user-agent)"


class GeocodeError(RuntimeError):
    """Raised when a free-text location cannot be resolved to coordinates."""


def geocode(query: str, user_agent: str = DEFAULT_USER_AGENT, timeout: float = 10.0) -> Tuple[float, float]:
    """Resolve a free-text location (postal code, city, address) to (lat, lon)."""

    response = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    response.raise_for_status()
    matches = response.json()
    if not matches:
        raise GeocodeError(f"No geocoding match found for {query!r}")
    match = matches[0]
    return float(match["lat"]), float(match["lon"])
