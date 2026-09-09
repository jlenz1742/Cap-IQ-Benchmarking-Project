"""Helpers for turning raw dealer-locator API results into flat records."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_BR_TAG_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


def _clean_hours(hours: Optional[List[Dict[str, Any]]], language: Optional[str] = None) -> str:
    """Collapse the API's ``shopHours``/``serviceHours`` list into one string.

    Each entry looks like ``{"language": "de", "description": "Mo: |07:00 -
    16:30 Uhr<br/>Di: ..."}``; there is normally one entry per language the
    dealer's opening hours are translated into.
    """

    if not hours:
        return ""
    chosen = hours
    if language:
        matching = [h for h in hours if h.get("language") == language]
        if matching:
            chosen = matching
    parts = []
    for entry in chosen:
        description = entry.get("description") or ""
        text = _BR_TAG_RE.sub(" | ", description)
        text = re.sub(r"\s+", " ", text).strip(" |")
        if text:
            parts.append(text)
    return " || ".join(parts)


def flatten_dealer(result: Dict[str, Any], language: Optional[str] = None) -> Dict[str, Any]:
    """Flatten one ``{"dealer": ..., "distance": ..., ...}`` search hit.

    ``result`` is one entry of the ``results`` array returned by
    :meth:`bosch_dealers_scraper.client.BoschDealerClient.search_offline_dealers`.
    """

    dealer = result.get("dealer", {}) or {}
    address = dealer.get("address", {}) or {}
    properties = result.get("properties", {}) or {}

    return {
        "dealer_id": dealer.get("id"),
        "name": dealer.get("name"),
        "website": dealer.get("website"),
        "street": address.get("street"),
        "street2": address.get("street2"),
        "zip": address.get("zip"),
        "city": address.get("city"),
        "province": address.get("province"),
        "country": address.get("country"),
        "phone": address.get("phone"),
        "email": address.get("email"),
        "fax": address.get("fax"),
        "mobile": address.get("mobile"),
        "latitude": address.get("latitude"),
        "longitude": address.get("longitude"),
        "distance_m": result.get("distance"),
        "rank": result.get("rank"),
        "retailer_types": "; ".join(dealer.get("retailerTypes") or []),
        "premium_partner": dealer.get("premium"),
        "expert": dealer.get("expert"),
        "premium_flagship": dealer.get("premiumFlagship"),
        "delivery_types": "; ".join(dealer.get("deliveryTypes") or []),
        "payment_methods": "; ".join(dealer.get("paymentMethods") or []),
        "open_now": dealer.get("openNow"),
        "closes_at": dealer.get("closesAt"),
        "benefits": "; ".join(dealer.get("benefits") or []),
        "badges": "; ".join(sorted(properties.keys())),
        "shop_hours": _clean_hours(dealer.get("shopHours"), language),
        "service_hours": _clean_hours(dealer.get("serviceHours"), language),
    }


FIELDNAMES = [
    "dealer_id",
    "name",
    "website",
    "street",
    "street2",
    "zip",
    "city",
    "province",
    "country",
    "phone",
    "email",
    "fax",
    "mobile",
    "latitude",
    "longitude",
    "distance_m",
    "rank",
    "retailer_types",
    "premium_partner",
    "expert",
    "premium_flagship",
    "delivery_types",
    "payment_methods",
    "open_now",
    "closes_at",
    "benefits",
    "badges",
    "shop_hours",
    "service_hours",
    "found_via_query",
]
