"""Command-line interface for the Bosch Professional dealer scraper.

Examples
--------
Search around a single coordinate::

    python -m bosch_dealers_scraper --lat 52.52 --lon 13.405 --radius-km 50 \\
        --output dealers_berlin.csv

Search around a free-text location (geocoded via OpenStreetMap Nominatim)::

    python -m bosch_dealers_scraper --location "10115 Berlin" --radius-km 25 \\
        --output dealers_berlin.csv

Sweep an entire country (default bounding box is Germany) and de-duplicate::

    python -m bosch_dealers_scraper --country-scan --output dealers_de.csv

Sweep a different known country via the ``--country`` shortcut::

    python -m bosch_dealers_scraper --country-scan --country fr --output dealers_fr.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from typing import Any, Dict, Iterable, List, Optional

from .client import DEFAULT_MARKET, MAX_SENSIBLE_RADIUS_M, BoschDealerClient, DealerLocatorError
from .geocode import GeocodeError, geocode
from .grid import COUNTRY_PRESETS, GERMANY_BBOX, generate_grid
from .models import FIELDNAMES, flatten_dealer

logger = logging.getLogger("bosch_dealers_scraper")


def _parse_bbox(raw: str) -> tuple:
    parts = [float(p.strip()) for p in raw.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "bbox must be 'lat_min,lon_min,lat_max,lon_max', got: " + raw
        )
    return tuple(parts)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bosch_dealers_scraper",
        description="Scrape dealer listings from the Bosch Professional dealer locator.",
    )
    location = parser.add_mutually_exclusive_group()
    location.add_argument(
        "--location",
        help="Free-text location (postal code, city, address) to search near. "
        "Geocoded via OpenStreetMap Nominatim.",
    )
    location.add_argument(
        "--lat",
        type=float,
        help="Latitude to search near (use together with --lon).",
    )
    parser.add_argument(
        "--lon",
        type=float,
        help="Longitude to search near (use together with --lat).",
    )
    location.add_argument(
        "--country-scan",
        action="store_true",
        help="Sweep an entire bounding box (default: Germany) with a grid of "
        "overlapping searches and de-duplicate the results by dealer id.",
    )

    parser.add_argument(
        "--radius-km",
        type=float,
        default=MAX_SENSIBLE_RADIUS_M / 1000,
        help=f"Search radius in km for a single-point search (default: "
        f"{MAX_SENSIBLE_RADIUS_M / 1000:g}, the site's own maximum).",
    )
    parser.add_argument(
        "--country",
        choices=sorted(COUNTRY_PRESETS),
        default=None,
        help="Shortcut that sets --market and --bbox for a known country "
        f"({', '.join(sorted(COUNTRY_PRESETS))}). Either can still be "
        "overridden explicitly.",
    )
    parser.add_argument(
        "--bbox",
        type=_parse_bbox,
        default=None,
        help="Bounding box for --country-scan as 'lat_min,lon_min,lat_max,lon_max' "
        "(default: Germany, or --country's bbox if set).",
    )
    parser.add_argument(
        "--spacing-km",
        type=float,
        default=120.0,
        help="Distance between grid points for --country-scan (default: 120). "
        "Keep this <= radius-km * sqrt(2) for full coverage.",
    )
    parser.add_argument(
        "--scan-radius-km",
        type=float,
        default=100.0,
        help="Search radius per grid point for --country-scan (default: 100, "
        "the site's own maximum).",
    )

    parser.add_argument(
        "--market",
        default=None,
        help="Bosch Professional market path, e.g. 'de/de', 'at/de', 'fr/fr', "
        f"'gb/en' (default: {DEFAULT_MARKET!r}, or --country's market if set). "
        "See robots.txt for every market's sitemap.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Minimum seconds between requests to the dealer locator (default: 1.0).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries per request before giving up (default: 3).",
    )
    parser.add_argument(
        "--user-agent",
        default=None,
        help="Custom User-Agent string sent with every request (also used for "
        "geocoding, where Nominatim asks for a descriptive value with contact info).",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="If set, prefer this language's opening-hours text when a dealer "
        "has more than one translation available (e.g. 'de').",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="-",
        help="Output file path. Defaults to stdout ('-').",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default=None,
        help="Output format. Inferred from --output's extension if omitted, "
        "otherwise defaults to csv.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (INFO-level) logging to stderr.",
    )
    return parser


def _infer_format(output: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    if output.lower().endswith(".json"):
        return "json"
    return "csv"


def _write_records(records: List[Dict[str, Any]], output: str, fmt: str) -> None:
    stream = sys.stdout if output == "-" else open(output, "w", newline="", encoding="utf-8")
    try:
        if fmt == "json":
            json.dump(records, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        else:
            writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for record in records:
                writer.writerow(record)
    finally:
        if stream is not sys.stdout:
            stream.close()


def _flatten_all(
    hits: Iterable[Dict[str, Any]], query_label: str, language: Optional[str]
) -> Iterable[Dict[str, Any]]:
    for hit in hits:
        record = flatten_dealer(hit, language=language)
        record["found_via_query"] = query_label
        yield record


def run_single_search(
    client: BoschDealerClient, lat: float, lon: float, radius_km: float, language: Optional[str]
) -> List[Dict[str, Any]]:
    result = client.search_offline_dealers(lat, lon, radius_m=int(radius_km * 1000))
    label = f"{lat:.5f},{lon:.5f}"
    logger.info("Found %d dealer(s) near %s (radius %.0f km)", len(result.results), label, radius_km)
    return list(_flatten_all(result.results, label, language))


def run_country_scan(
    client: BoschDealerClient,
    bbox: tuple,
    spacing_km: float,
    radius_km: float,
    language: Optional[str],
) -> List[Dict[str, Any]]:
    points = list(generate_grid(bbox, spacing_km))
    logger.info(
        "Scanning %d grid point(s) across bbox=%s (spacing=%.0fkm, radius=%.0fkm)",
        len(points),
        bbox,
        spacing_km,
        radius_km,
    )
    by_id: Dict[str, Dict[str, Any]] = {}
    for i, point in enumerate(points, start=1):
        label = f"{point.latitude:.5f},{point.longitude:.5f}"
        try:
            result = client.search_offline_dealers(
                point.latitude, point.longitude, radius_m=int(radius_km * 1000)
            )
        except DealerLocatorError as exc:
            logger.warning("Query %d/%d (%s) failed, skipping: %s", i, len(points), label, exc)
            continue
        new_count = 0
        for hit in result.results:
            dealer_id = (hit.get("dealer") or {}).get("id")
            key = dealer_id or f"unkeyed:{label}:{hit.get('distance')}"
            if key not in by_id:
                record = flatten_dealer(hit, language=language)
                record["found_via_query"] = label
                by_id[key] = record
                new_count += 1
        logger.info(
            "Query %d/%d (%s): %d hit(s), %d new, %d unique so far",
            i,
            len(points),
            label,
            len(result.results),
            new_count,
            len(by_id),
        )
    return list(by_id.values())


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.country_scan and args.location is None and args.lat is None:
        parser.error("Specify one of --location, --lat/--lon, or --country-scan")
    if args.lat is not None and args.lon is None:
        parser.error("--lat requires --lon")

    preset_market, preset_bbox = COUNTRY_PRESETS.get(args.country, (DEFAULT_MARKET, GERMANY_BBOX))
    market = args.market or preset_market
    bbox = args.bbox or preset_bbox

    client_kwargs: Dict[str, Any] = dict(
        market=market,
        request_delay=args.delay,
        max_retries=args.max_retries,
    )
    if args.user_agent:
        client_kwargs["user_agent"] = args.user_agent
    client = BoschDealerClient(**client_kwargs)

    try:
        if args.country_scan:
            records = run_country_scan(
                client, bbox, args.spacing_km, args.scan_radius_km, args.language
            )
        else:
            if args.location is not None:
                geocode_kwargs = {}
                if args.user_agent:
                    geocode_kwargs["user_agent"] = args.user_agent
                lat, lon = geocode(args.location, **geocode_kwargs)
                logger.info("Geocoded %r to (%.5f, %.5f)", args.location, lat, lon)
            else:
                lat, lon = args.lat, args.lon
            records = run_single_search(client, lat, lon, args.radius_km, args.language)
    except (DealerLocatorError, GeocodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    fmt = _infer_format(args.output, args.format)
    _write_records(records, args.output, fmt)
    if args.output != "-":
        print(f"Wrote {len(records)} dealer(s) to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
