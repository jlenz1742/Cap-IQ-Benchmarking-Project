"""Scraper for Makita USA's "Buy Local" dealer locator (makitatools.com).

Unlike the German site (see ``client.py``), makitatools.com does not run
the third-party "dealerlocator" widget. It has its own custom locator
(Leaflet map + a ``GeoSearch`` JS module, see
``/products/buy-local``) backed by a geo-radius search API:

    GET /api/getretailersbyretailertypewithinmiles
        ?zip=<zip>&lat=<lat>&lon=<lon>&miles=<radius, max 200>&retailerType=<bitmask, 0 = all>

There is no "give me everything" mode, so full US coverage is done by
querying a grid of points spanning the country at the widget's maximum
200-mile radius and de-duplicating the results (the API returns no stable
id, so dealers are de-duplicated by name + street + zip).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Iterable

import requests

from .client import DEFAULT_HEADERS, Dealer
from .ssl_utils import ca_bundle_with_godaddy_intermediate

logger = logging.getLogger(__name__)

US_BASE_URL = "https://www.makitatools.com"
US_RETAILERS_PATH = "/api/getretailersbyretailertypewithinmiles"
US_MAX_RADIUS_MILES = 200
US_RETAILER_TYPE_ALL = 0  # 0 = no type filter applied server-side (all dealers)

MILES_PER_LAT_DEGREE = 69.0


@dataclass(frozen=True)
class BoundingBox:
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


# Coarse boxes covering where Makita USA dealers can actually be: the
# contiguous US, Alaska's populated south/southeast coast, the main
# Hawaiian islands, and Puerto Rico. Grid points that land over open ocean
# or empty wilderness just come back with distant/no results; that's a
# cheap no-op, not a correctness problem.
US_REGIONS: tuple[BoundingBox, ...] = (
    BoundingBox("conus", 24.5, 49.5, -125.0, -66.5),
    BoundingBox("alaska", 55.0, 71.0, -170.0, -130.0),
    BoundingBox("hawaii", 18.5, 22.5, -160.5, -154.5),
    BoundingBox("puerto_rico", 17.8, 18.6, -67.5, -65.2),
)


def _miles_per_lon_degree(lat: float) -> float:
    return 69.172 * math.cos(math.radians(lat))


def _linspace_inclusive(start: float, end: float, step: float) -> list[float]:
    """Evenly spaced points from ``start`` to ``end`` inclusive, with actual
    spacing <= ``step``.

    A naive ``start, start+step, start+2*step, ...`` walk can stop one
    short of ``end`` (whenever the span isn't an exact multiple of
    ``step``), leaving a gap up to a full ``step`` wide right at the
    boundary uncovered. Fixing the point count and *then* spacing points
    evenly across the exact span guarantees both endpoints are hit and no
    edge gap exists.
    """
    span = end - start
    if span <= 0:
        return [start]
    n = max(1, math.ceil(span / step)) + 1
    if n == 1:
        return [start]
    return [start + i * span / (n - 1) for i in range(n)]


def build_search_grid(
    regions: Iterable[BoundingBox] = US_REGIONS, spacing_miles: float = 250.0
) -> list[tuple[float, float]]:
    """Generate lat/lon grid points spaced so 200-mile search circles overlap.

    For a square grid, the point farthest from its four nearest grid
    corners (a cell's center) is ``spacing / sqrt(2)`` away. Keeping
    ``spacing_miles`` comfortably under ``US_MAX_RADIUS_MILES * sqrt(2)``
    (~283 mi) guarantees every interior point in a region lies within
    ``US_MAX_RADIUS_MILES`` of some grid center. Rows and columns are laid
    out with ``_linspace_inclusive`` so the box's own edges are always
    exactly covered too, not just its interior.
    """
    points: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()

    for box in regions:
        lat_step = spacing_miles / MILES_PER_LAT_DEGREE
        for lat in _linspace_inclusive(box.lat_min, box.lat_max, lat_step):
            lon_step = spacing_miles / _miles_per_lon_degree(lat)
            for lon in _linspace_inclusive(box.lon_min, box.lon_max, lon_step):
                point = (round(lat, 4), round(lon, 4))
                if point not in seen:
                    seen.add(point)
                    points.append(point)

    return points


class USDealerLocatorClient:
    """Talks to makitatools.com's geo-radius retailer search API."""

    def __init__(
        self,
        timeout: float = 30.0,
        session: requests.Session | None = None,
        request_delay: float = 0.25,
    ):
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session.headers.update(
            {
                "Referer": US_BASE_URL + "/products/buy-local",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            }
        )
        # See ssl_utils.py: makitatools.com omits its intermediate cert.
        self.session.verify = ca_bundle_with_godaddy_intermediate()
        self.request_delay = request_delay

    def _search_point(self, lat: float, lon: float) -> list[dict[str, Any]]:
        params = {
            "zip": "",
            "lat": lat,
            "lon": lon,
            "miles": US_MAX_RADIUS_MILES,
            "retailerType": US_RETAILER_TYPE_ALL,
            "shopEventId": "",
        }
        # Passed explicitly (not just set on the session) so it wins over
        # a REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE env var: requests only
        # consults session.verify when the per-call value is left as the
        # default None, in which case it lets those env vars override it.
        response = self.session.get(
            US_BASE_URL + US_RETAILERS_PATH,
            params=params,
            timeout=self.timeout,
            verify=self.session.verify,
        )
        response.raise_for_status()
        return response.json()

    def fetch_all_dealers(
        self, grid: Iterable[tuple[float, float]] | None = None
    ) -> list[Dealer]:
        grid = list(grid) if grid is not None else build_search_grid()
        logger.info("Searching %d grid points across the US", len(grid))

        raw_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
        for i, (lat, lon) in enumerate(grid, start=1):
            try:
                results = self._search_point(lat, lon)
            except requests.RequestException as exc:
                logger.warning("Grid point %.2f,%.2f failed: %s", lat, lon, exc)
                continue

            for raw in results:
                key = (
                    str(raw.get("Name", "")).strip().lower(),
                    str(raw.get("Address1", "")).strip().lower(),
                    str(raw.get("Zip", "")).strip().lower(),
                )
                raw_by_key.setdefault(key, raw)

            if i % 10 == 0 or i == len(grid):
                logger.info(
                    "Searched %d/%d grid points, %d unique dealers so far",
                    i,
                    len(grid),
                    len(raw_by_key),
                )

            if self.request_delay:
                time.sleep(self.request_delay)

        logger.info("Found %d unique US dealers", len(raw_by_key))
        return [Dealer.from_us_raw(raw) for raw in raw_by_key.values()]
