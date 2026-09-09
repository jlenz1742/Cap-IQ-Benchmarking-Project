"""Command-line entry point.

Examples
--------
Scrape every German dealer/retailer to CSV::

    python -m scrapers.dewalt.cli --country DE

Scrape only US online retailers, as JSON, with more logging::

    python -m scrapers.dewalt.cli --country US --purpose online-retailer \\
        --format json -v
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

from .client import PURPOSES
from .countries import COUNTRIES
from .scraper import scrape_country, write_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape DeWalt dealer/retailer locations from the official store locator."
    )
    parser.add_argument(
        "--country",
        required=True,
        choices=sorted(COUNTRIES),
        help="Country to scrape. See countries.py to add more.",
    )
    parser.add_argument(
        "--purpose",
        nargs="+",
        choices=PURPOSES,
        default=None,
        help=f"Dealer categories to fetch (default: all of {list(PURPOSES)}).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Page size requested from the API (default: 200).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Delay in seconds between paginated requests (default: 0.4).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: output/dewalt_<country>.<format>).",
    )
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    country = COUNTRIES[args.country]
    output = args.output or Path("output") / f"dewalt_{country.code.lower()}.{args.format}"

    rows = scrape_country(
        country,
        purposes=args.purpose,
        limit=args.limit,
        request_delay=args.delay,
    )

    if args.format == "csv":
        write_csv(rows, output)
    else:
        write_json(rows, output)

    print(f"Wrote {len(rows)} dealer location(s) for {country.name} to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
