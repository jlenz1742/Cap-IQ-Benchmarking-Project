"""Generate a grid of search points covering a bounding box.

A single dealer-locator query only returns dealers near one coordinate (and
the backend silently caps how many it returns), so scraping every dealer in
a country means tiling it with overlapping search circles and de-duplicating
the results by dealer id. This module builds that tiling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterator, Tuple

KM_PER_DEGREE_LAT = 111.32

# Rough bounding boxes as (lat_min, lon_min, lat_max, lon_max).
GERMANY_BBOX: Tuple[float, float, float, float] = (47.2, 5.5, 55.1, 15.5)
# Mainland France plus Corsica.
FRANCE_BBOX: Tuple[float, float, float, float] = (41.3, -5.2, 51.1, 9.6)

# --country presets for the CLI: name -> (market path, default bbox).
COUNTRY_PRESETS: Dict[str, Tuple[str, Tuple[float, float, float, float]]] = {
    "de": ("de/de", GERMANY_BBOX),
    "fr": ("fr/fr", FRANCE_BBOX),
}


@dataclass(frozen=True)
class GridPoint:
    latitude: float
    longitude: float


def generate_grid(
    bbox: Tuple[float, float, float, float],
    spacing_km: float,
) -> Iterator[GridPoint]:
    """Yield grid points spaced ``spacing_km`` apart across ``bbox``.

    ``bbox`` is ``(lat_min, lon_min, lat_max, lon_max)``. Longitude spacing is
    widened towards the poles (1 degree of longitude covers fewer km as
    ``|latitude|`` grows) so the physical spacing stays roughly constant.

    To fully cover the area with circular queries of radius ``r``, choose
    ``spacing_km`` no larger than ``r * sqrt(2)`` (so adjacent grid points,
    which can be up to ``spacing_km`` apart diagonally, still overlap) --
    e.g. spacing=120km pairs safely with a 100km query radius.
    """

    lat_min, lon_min, lat_max, lon_max = bbox
    if lat_min >= lat_max or lon_min >= lon_max:
        raise ValueError(f"Invalid bounding box: {bbox!r}")
    if spacing_km <= 0:
        raise ValueError("spacing_km must be positive")

    lat_step = spacing_km / KM_PER_DEGREE_LAT
    lat = lat_min
    while lat <= lat_max:
        km_per_degree_lon = KM_PER_DEGREE_LAT * math.cos(math.radians(lat))
        km_per_degree_lon = max(km_per_degree_lon, 1e-6)
        lon_step = spacing_km / km_per_degree_lon
        lon = lon_min
        while lon <= lon_max:
            yield GridPoint(latitude=round(lat, 5), longitude=round(lon, 5))
            lon += lon_step
        lat += lat_step
