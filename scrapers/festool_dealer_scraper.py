#!/usr/bin/env python3
"""
Festool US dealer scraper.

Festool's "Find a Dealer" page (https://www.festoolusa.com/dealer) embeds a
store-locator widget from Locally.com (festool.locally.com). That widget's
underlying data endpoint is a plain JSON API that returns every dealer
("marker") within a given radius of a lat/lng point:

    GET https://festool.locally.com/stores/conversion_data
        ?company_id=261617
        &dealers_company_id=261617
        &map_center_lat=<lat>
        &map_center_lng=<lng>
        &map_distance_diag=<radius in miles-ish, it's the map's diagonal>
        &only_show_country=US
        &sort_by=proximity
        ...

No authentication, cookies, or API key is required -- it's the same request
the public map widget makes from the browser. A single request centered on
the continental US with a large enough radius already returns the full,
untruncated dealer list (confirmed by cross-checking against several
regional queries), but this script queries a grid of overlapping regions
covering the whole country (CONUS + Alaska + Hawaii) and de-duplicates by
store id, so results stay complete even if any single query is ever capped.

This only reads the same public JSON the dealer-locator widget already
serves to every site visitor; it does not bypass auth or rate limiting.
Be a polite citizen: keep the request delay, and don't hammer the endpoint.

Usage:
    python3 festool_dealer_scraper.py [-o dealers.csv] [--json dealers.json]
                                       [--delay 0.75]

Output columns:
    id, name, address, city, state, zip, phone, lat, lng, is_claimed,
    timezone, slug, dealer_page_url
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass, fields
from typing import Iterable

import requests

ENDPOINT = "https://festool.locally.com/stores/conversion_data"
COMPANY_ID = "261617"  # Festool's Locally.com company id
REFERER = "https://festool.locally.com/stores/map/embedded?action=convert"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# A grid of (label, center_lat, center_lng, radius_diag_miles) covering the
# whole US. Radii are generous and cells overlap on purpose -- duplicates
# are removed afterwards by store id, so over-covering is harmless and
# under-covering is the only real risk.
GRID: list[tuple[str, float, float, float]] = [
    # Full-country sweep first (cheap belt-and-suspenders pass).
    ("CONUS-wide", 39.5, -98.35, 3200),
    # Regional overlapping cells across the continental US.
    ("NW", 46.5, -120.0, 900),
    ("W", 40.0, -119.0, 900),
    ("SW", 33.5, -112.0, 900),
    ("N-Central", 46.0, -100.0, 900),
    ("Central", 39.0, -98.0, 900),
    ("S-Central", 31.5, -97.0, 900),
    ("Great Lakes", 43.5, -86.0, 900),
    ("Ohio Valley", 38.5, -84.0, 900),
    ("Gulf", 31.0, -88.0, 900),
    ("Mid-Atlantic", 39.5, -78.0, 900),
    ("NE", 43.0, -72.0, 900),
    ("SE", 32.5, -81.5, 900),
    ("FL", 27.8, -81.6, 500),
    # Non-contiguous states need their own cells.
    ("Alaska", 64.0, -152.0, 2200),
    ("Hawaii", 20.7, -156.5, 500),
]

FIELDNAMES = [
    "id",
    "name",
    "address",
    "city",
    "state",
    "zip",
    "phone",
    "lat",
    "lng",
    "is_claimed",
    "timezone",
    "slug",
    "dealer_page_url",
]


@dataclass
class Dealer:
    id: int
    name: str
    address: str
    city: str
    state: str
    zip: str
    phone: str
    lat: str
    lng: str
    is_claimed: int
    timezone: str
    slug: str
    dealer_page_url: str

    @classmethod
    def from_marker(cls, m: dict) -> "Dealer":
        slug = m.get("slug") or ""
        return cls(
            id=m["id"],
            name=(m.get("name") or "").strip(),
            address=(m.get("address") or "").strip(),
            city=(m.get("city") or "").strip(),
            state=(m.get("state") or "").strip(),
            zip=(m.get("zip") or "").strip(),
            phone=(m.get("phone") or "").strip(),
            lat=m.get("lat", ""),
            lng=m.get("lng", ""),
            is_claimed=m.get("is_claimed") or 0,
            timezone=m.get("timezone") or "",
            slug=slug,
            dealer_page_url=(
                f"https://festool.locally.com/stores/{slug}" if slug else ""
            ),
        )


def fetch_region(
    session: requests.Session,
    lat: float,
    lng: float,
    diag: float,
    retries: int = 3,
    timeout: int = 30,
) -> list[dict]:
    """Fetch one grid cell's worth of dealer markers. Returns raw marker dicts."""
    params = {
        "has_data": 1,
        "company_id": COMPANY_ID,
        "dealers_company_id": COMPANY_ID,
        "inline": 1,
        "map_center_lat": lat,
        "map_center_lng": lng,
        "map_distance_diag": diag,
        "sort_by": "proximity",
        "zoom_level": 4,
        "only_show_country": "US",
    }
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(ENDPOINT, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("markers", [])
        except (requests.RequestException, ValueError) as exc:
            last_err = exc
            wait = 2 ** attempt
            print(
                f"  ! request failed ({exc}); retrying in {wait}s "
                f"({attempt}/{retries})",
                file=sys.stderr,
            )
            time.sleep(wait)
    raise RuntimeError(f"giving up on region ({lat}, {lng}, {diag}): {last_err}")


def scrape_all_dealers(delay: float = 0.75) -> list[Dealer]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Referer": REFERER,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }
    )

    by_id: dict[int, dict] = {}
    for label, lat, lng, diag in GRID:
        print(f"Fetching region '{label}' (center {lat},{lng} diag {diag}mi)...")
        markers = fetch_region(session, lat, lng, diag)
        new = 0
        for m in markers:
            if m.get("country") != "US":
                continue
            if m["id"] not in by_id:
                new += 1
            by_id[m["id"]] = m
        print(f"  -> {len(markers)} markers returned, {new} new")
        time.sleep(delay)

    dealers = [Dealer.from_marker(m) for m in by_id.values()]
    dealers.sort(key=lambda d: (d.state, d.city, d.name))
    return dealers


def write_csv(dealers: Iterable[Dealer], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for d in dealers:
            writer.writerow({fname: getattr(d, fname) for fname in FIELDNAMES})


def write_json(dealers: Iterable[Dealer], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            [{fname: getattr(d, fname) for fname in FIELDNAMES} for d in dealers],
            f,
            indent=2,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        default="festool_dealers_us.csv",
        help="CSV output path (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        default=None,
        help="Optional JSON output path",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.75,
        help="Seconds to sleep between requests (default: %(default)s)",
    )
    args = parser.parse_args()

    dealers = scrape_all_dealers(delay=args.delay)

    write_csv(dealers, args.output)
    print(f"\nWrote {len(dealers)} dealers to {args.output}")

    if args.json_output:
        write_json(dealers, args.json_output)
        print(f"Wrote {len(dealers)} dealers to {args.json_output}")

    from collections import Counter

    by_state = Counter(d.state for d in dealers)
    print("\nDealers by state:")
    for state, count in sorted(by_state.items()):
        print(f"  {state:>3}  {count}")
    print(f"  {'ALL':>3}  {sum(by_state.values())}")


if __name__ == "__main__":
    main()
