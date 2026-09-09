"""HTTP client for the Bosch Professional dealer-locator backend.

The public dealer-search page at ``https://www.bosch-professional.com/<market>/dealers/``
is a JavaScript single-page widget. It does not expose its data through any
static HTML, so this client talks to the same JSON endpoint the page itself
calls once a visitor searches for a location:

    POST https://www.bosch-professional.com/<market>/dealers/retailers/offline
    Content-Type: application/x-www-form-urlencoded
    latitude=<float>&longitude=<float>&radius=<meters>

``<market>`` is the two-letter country code and language used throughout the
site (e.g. ``de/de``, ``at/de``, ``fr/fr``, ``gb/en`` -- see the sitemap list
in ``robots.txt`` for every market Bosch Professional operates).

The endpoint returns every dealer within ``radius`` metres of the given
coordinate, ordered by distance, capped at a few hundred results. Because a
single query cannot return an entire country's dealer network, covering a
whole country requires tiling it with many smaller-radius queries and
de-duplicating by dealer id -- see :mod:`bosch_dealers_scraper.grid` and
:mod:`bosch_dealers_scraper.cli`.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_MARKET = "de/de"
DEFAULT_BASE_HOST = "https://www.bosch-professional.com"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# The site's own UI only offers these radii (in metres), and the backend has
# been observed to silently cap results at ~1000 once a query's radius grows
# much beyond this, so there is no benefit to requesting more.
MAX_SENSIBLE_RADIUS_M = 100_000


class DealerLocatorError(RuntimeError):
    """Raised when the dealer-locator endpoint cannot be queried successfully."""


@dataclass
class SearchResult:
    """Raw result of one dealer-locator query."""

    results: List[Dict[str, Any]]
    default_filters: List[Dict[str, Any]]
    filter_categories: List[Dict[str, Any]]


class BoschDealerClient:
    """Thin wrapper around the Bosch Professional dealer-locator API."""

    def __init__(
        self,
        market: str = DEFAULT_MARKET,
        base_host: str = DEFAULT_BASE_HOST,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 20.0,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
        request_delay: float = 1.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.market = market.strip("/")
        self.base_host = base_host.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.request_delay = request_delay
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Referer": self.dealers_page_url,
            }
        )
        self._last_request_time = 0.0

    @property
    def dealers_page_url(self) -> str:
        return f"{self.base_host}/{self.market}/dealers/"

    @property
    def offline_api_url(self) -> str:
        return f"{self.base_host}/{self.market}/dealers/retailers/offline"

    @property
    def online_api_url(self) -> str:
        return f"{self.base_host}/{self.market}/dealers/retailers/online"

    def _throttle(self) -> None:
        if self.request_delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        wait = self.request_delay - elapsed
        if wait > 0:
            time.sleep(wait)

    def _post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            self._last_request_time = time.monotonic()
            try:
                response = self.session.post(url, data=data, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    "Dealer-locator request failed (attempt %d/%d): HTTP %d for %s %r",
                    attempt,
                    self.max_retries,
                    response.status_code,
                    url,
                    data,
                )
                last_exc = DealerLocatorError(
                    f"HTTP {response.status_code} from {url} (params={data})"
                )
            except requests.RequestException as exc:  # network error, timeout, etc.
                logger.warning(
                    "Dealer-locator request errored (attempt %d/%d): %s", attempt, self.max_retries, exc
                )
                last_exc = exc
            if attempt < self.max_retries:
                time.sleep(self.retry_backoff * attempt)
        assert last_exc is not None
        raise DealerLocatorError(str(last_exc)) from last_exc

    def search_offline_dealers(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = MAX_SENSIBLE_RADIUS_M,
    ) -> SearchResult:
        """Return every physical Bosch dealer within ``radius_m`` metres of a point."""

        payload = self._post(
            self.offline_api_url,
            {"latitude": latitude, "longitude": longitude, "radius": int(radius_m)},
        )
        return SearchResult(
            results=payload.get("results", []) or [],
            default_filters=payload.get("defaultFilters", []) or [],
            filter_categories=payload.get("filterCategories", []) or [],
        )
