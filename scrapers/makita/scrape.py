"""CLI to scrape Makita's dealer locator for one country.

Usage:
    python -m scrapers.makita.scrape --country de
    python -m scrapers.makita.scrape --country de --out output/makita/de/dealers.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

from .client import DEALER_FIELDS, DealerLocatorClient
from .countries import COUNTRIES, get_country

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--country",
        default="de",
        choices=sorted(COUNTRIES),
        help="Country code to scrape (default: de).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Output CSV path. Defaults to "
            "output/makita/<country>/dealers.csv"
        ),
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to also write the raw dealer list as JSON.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )
    return parser.parse_args(argv)


def write_csv(dealers, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DEALER_FIELDS)
        writer.writeheader()
        for dealer in dealers:
            writer.writerow({field: getattr(dealer, field) for field in DEALER_FIELDS})


def write_json(dealers, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            [{field: getattr(d, field) for field in DEALER_FIELDS} for d in dealers],
            f,
            ensure_ascii=False,
            indent=2,
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    country = get_country(args.country)
    out_path = args.out or REPO_ROOT / "output" / "makita" / country.code / "dealers.csv"

    client = DealerLocatorClient(country)
    dealers = client.fetch_all_dealers()

    if not dealers:
        logging.warning("No dealers returned for %s; not writing an empty file.", country.name)
        return 1

    write_csv(dealers, out_path)
    logging.info("Wrote %d dealers to %s", len(dealers), out_path)

    if args.json_out:
        write_json(dealers, args.json_out)
        logging.info("Wrote %d dealers to %s", len(dealers), args.json_out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
