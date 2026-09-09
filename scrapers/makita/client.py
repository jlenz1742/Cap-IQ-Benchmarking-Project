"""HTTP client for Makita's "dealerlocator" widget JSON endpoint."""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass, fields
from typing import Any

import requests

from .countries import CountryConfig

logger = logging.getLogger(__name__)

DEALERLOCATOR_PATH = "/crm/front/dealerlocator/dealerlocator_ajax.asp"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}


@dataclass(frozen=True)
class Dealer:
    """A single, cleaned-up dealer record."""

    source_id: str
    customer_number: str | None
    name: str
    company_1: str | None
    company_2: str | None
    company_3: str | None
    dealer_type: str | None
    street: str
    house_number: str | None
    postcode: str
    city: str
    phone: str | None
    fax: str | None
    email: str | None
    website: str | None
    latitude: float | None
    longitude: float | None
    geocoded_address: str | None
    extra_info: str | None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "Dealer":
        def s(key: str) -> str | None:
            value = raw.get(key)
            if value is None:
                return None
            # Some source records are multiply HTML-encoded (e.g.
            # "K&amp;amp;#246;niginhofstr."), so unescape until it stabilizes.
            # A no-op pass on normal, singly-encoded text exits immediately.
            value = str(value)
            for _ in range(5):
                unescaped = html.unescape(value)
                if unescaped == value:
                    break
                value = unescaped
            value = value.strip()
            return value or None

        def f(key: str) -> float | None:
            value = raw.get(key)
            try:
                return float(value) if value not in (None, "") else None
            except (TypeError, ValueError):
                return None

        return cls(
            source_id=s("recordset_id") or "",
            customer_number=s("recordset_debiteur_nr"),
            name=s("bedrijfsnaam") or s("recordset_bedrijfsnaam") or "",
            company_1=s("recordset_company_1"),
            company_2=s("recordset_company_2"),
            company_3=s("recordset_company_3"),
            dealer_type=s("recordset_dealer_type"),
            street=s("adres") or "",
            house_number=s("huisnummer"),
            postcode=s("postcode") or "",
            city=s("plaats") or "",
            phone=s("recordset_telefoon"),
            fax=s("recordset_fax"),
            email=s("recordset_email") or s("email"),
            website=s("recordset_webshop_website"),
            latitude=f("lat"),
            longitude=f("lng"),
            geocoded_address=s("recordset_geocode"),
            extra_info=s("recordset_extra_informatie"),
        )


DEALER_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(Dealer))


class DealerLocatorClient:
    """Talks to one Makita country site's dealerlocator widget."""

    def __init__(self, country: CountryConfig, timeout: float = 30.0, session: requests.Session | None = None):
        self.country = country
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_all_dealers(self) -> list[Dealer]:
        """Fetch every dealer for this country in a single request.

        The widget supports a "show all dealers" mode (used by the site's
        results table / list view) that returns the complete, ungated
        dealer list in one JSON payload instead of requiring a postcode
        search + privacy-mode unlock.
        """
        url = self.country.base_url + DEALERLOCATOR_PATH
        payload = {
            "search": "",
            "filter_must_be_active_on_search": "false",
            "search_type": "",
            "dealer_filters": "",
            "show_all_dealers": "true",
            "show_all_dealers_list": "true",
            "show_per_display_type": "false",
            "query_id": self.country.query_id,
            "countries_for_results": self.country.countries_for_results,
            "overrule_zipcode_check": "",
            "use_miles": "0",
            "city_search_nodes": "",
            "dealerlocator_search_distance": "",
            "dealerlocator_id": self.country.dealerlocator_id,
            "use_filter_immediately": "0",
            "extra_search_condition": self.country.extra_search_condition,
            "privacy_mode": "true",
            "location_needs_to_have_all_filters": "false",
            "maps_functional_consent": "1",
            "uc_cmp_active": "0",
        }

        logger.info("Requesting dealer list for %s from %s", self.country.name, url)
        response = self.session.post(url, data=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        status = data.get("status")
        if status != "OK":
            raise RuntimeError(
                f"dealerlocator endpoint returned status={status!r} "
                f"(response kept dealers hidden, e.g. privacy mode was not lifted)"
            )

        raw_dealers = data.get("dealers") or []
        logger.info("Received %d dealer records for %s", len(raw_dealers), self.country.name)
        return [Dealer.from_raw(raw) for raw in raw_dealers]
