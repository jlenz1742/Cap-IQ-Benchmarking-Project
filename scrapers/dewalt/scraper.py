"""Orchestrates the store-locator client into a full-country dealer dump."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from .client import PURPOSES, StoreLocatorClient
from .countries import Country

logger = logging.getLogger(__name__)

FIELDNAMES = [
    "id",
    "name",
    "source_purpose",
    "purpose_codes",
    "brands",
    "premium",
    "is_online_only",
    "is_head_quarter",
    "market_or_country",
    "address1",
    "address2",
    "city",
    "state",
    "postal_code",
    "latitude",
    "longitude",
    "phone",
    "email",
    "website",
    "organization_name",
    "google_rating",
    "google_reviews_total",
    "created_at",
    "updated_at",
]


def flatten(item: dict, source_purpose: str) -> dict:
    """Reduce one raw API record to a flat row suitable for CSV/spreadsheet use."""
    address = item.get("address") or {}
    contact = item.get("contact") or {}
    coordinates = address.get("coordinates") or [None, None]
    organization = item.get("organization_data") or {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "source_purpose": source_purpose,
        "purpose_codes": ",".join(item.get("purpose_codes") or []),
        "brands": ",".join(item.get("brands") or []),
        "premium": item.get("premium"),
        "is_online_only": item.get("is_online_only"),
        "is_head_quarter": item.get("is_head_quarter"),
        "market_or_country": item.get("market_or_country"),
        "address1": address.get("address1"),
        "address2": address.get("address2"),
        "city": address.get("city"),
        "state": address.get("state"),
        "postal_code": address.get("postal_code"),
        "latitude": coordinates[0] if len(coordinates) > 0 else None,
        "longitude": coordinates[1] if len(coordinates) > 1 else None,
        "phone": contact.get("phone"),
        "email": contact.get("email"),
        "website": contact.get("website"),
        "organization_name": organization.get("name"),
        "google_rating": item.get("google_rating"),
        "google_reviews_total": item.get("google_reviews_total"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def scrape_country(
    country: Country,
    purposes: Optional[Sequence[str]] = None,
    limit: int = 200,
    request_delay: float = 0.4,
    client: Optional[StoreLocatorClient] = None,
) -> list[dict]:
    """Fetch every dealer location listed for ``country``.

    Queries each requested purpose ("store-retailer", "online-retailer",
    "service-center") in turn and paginates each one to completion.
    A dealer can legitimately be listed under more than one purpose, so
    results are deduplicated by dealer id before being returned.
    """
    purposes = list(purposes) if purposes else list(PURPOSES)
    client = client or StoreLocatorClient(country.domain, request_delay=request_delay)

    seen: dict[str, dict] = {}
    for purpose in purposes:
        count_before = len(seen)
        for page in client.iter_pages(purpose, country.lang, limit=limit):
            for item in page.get("items", []):
                dealer_id = item.get("id")
                if dealer_id and dealer_id not in seen:
                    seen[dealer_id] = flatten(item, purpose)
        logger.info(
            "%s / %s: %d new dealer(s)", country.name, purpose, len(seen) - count_before
        )

    logger.info("%s: %d unique dealer location(s) collected", country.name, len(seen))
    return list(seen.values())


def write_csv(rows: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(rows), f, ensure_ascii=False, indent=2)
