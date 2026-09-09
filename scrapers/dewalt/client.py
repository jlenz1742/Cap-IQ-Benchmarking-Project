"""Thin HTTP client for DeWalt's store-locator API.

The store-locator page calls ``POST https://<domain>/api/store-locator``
with a small JSON body and gets back a page of dealer locations plus a
``next`` cursor for the following page. This client reproduces exactly that
request/response cycle so it can be reused for any purpose (a full-country
listing, a geo-radius search around a postcode, etc.) without a browser.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Iterator, Mapping, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# The three dealer categories the store-locator UI itself offers
# ("Lokale Händler" / "Online-Händler" / "Servicecenter" on the German
# site). This is the exhaustive, server-validated enum -- any other value
# is rejected by the API with a Zod validation error.
PURPOSES = ("store-retailer", "online-retailer", "service-center")


class StoreLocatorError(RuntimeError):
    """Raised when the store-locator API returns an error payload."""


class StoreLocatorClient:
    """Client for one country's ``/api/store-locator`` endpoint."""

    def __init__(
        self,
        domain: str,
        timeout: float = 20.0,
        request_delay: float = 0.4,
        user_agent: str = DEFAULT_USER_AGENT,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.domain = domain
        self.base_url = f"https://{domain}/api/store-locator"
        self.timeout = timeout
        self.request_delay = request_delay
        self.session = session or self._build_session(domain, user_agent)

    @staticmethod
    def _build_session(domain: str, user_agent: str) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"POST"}),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "User-Agent": user_agent,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": f"https://{domain}",
                "Referer": f"https://{domain}/",
            }
        )
        return session

    def fetch(self, body: Mapping[str, Any]) -> dict:
        """POST one request body and return the ``result`` payload."""
        response = self.session.post(self.base_url, json=body, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise StoreLocatorError(f"{self.domain}: {data['error']}")
        return data["result"]

    def iter_pages(
        self,
        purpose: str,
        lang: str,
        limit: int = 200,
        coordinates: Optional[str] = None,
        radius: Optional[float] = None,
        distance_unit: str = "Km",
        name: Optional[str] = None,
    ) -> Iterator[dict]:
        """Yield successive ``result`` pages for one dealer category.

        With no ``coordinates`` given, the API returns *every* location
        listed for the country implied by ``lang``, paginated by ``limit``.
        Passing ``coordinates`` ("lat,lon") and ``radius`` instead performs
        a geo-radius search around that point, matching what the "use my
        location" / postcode search on the site itself does.
        """
        if purpose not in PURPOSES:
            raise ValueError(f"purpose must be one of {PURPOSES}, got {purpose!r}")

        body: dict[str, Any] = {"purpose": purpose, "lang": lang, "limit": limit}
        if coordinates:
            body["coordinates"] = coordinates
            body["radius"] = radius
            body["distance_unit"] = distance_unit
        if name:
            body["name"] = name

        page_num = 0
        while True:
            result = self.fetch(body)
            page_num += 1
            items = result.get("items", [])
            logger.info(
                "%s purpose=%s page=%d items=%d (total so far: %d/%s)",
                self.domain,
                purpose,
                page_num,
                len(items),
                page_num * limit if page_num * limit < result.get("grand_total", 0) else result.get("grand_total", 0),
                result.get("grand_total"),
            )
            yield result

            next_param = result.get("next")
            if not next_param:
                break
            # The API hands back a ready-made query string for the next
            # page; the follow-up request just wraps it as `param`.
            body = {"param": next_param, "lang": lang, "purpose": purpose}
            if self.request_delay:
                time.sleep(self.request_delay)
