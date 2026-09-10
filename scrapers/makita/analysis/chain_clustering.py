"""Cluster Makita US dealers by parent chain and summarize the result.

Reads output/makita/us/dealers.csv (see scrapers/makita/us.py) and groups
dealer listings into named parent chains by regex pattern matching on the
dealer name (merging store-number suffixes and known brand-name variants,
e.g. "HOME DEPOT #6521" and "THE HOME DEPOT" both -> "The Home Depot").
Everything that doesn't match a known chain pattern falls into "All Other
Dealers" (smaller regional chains and true independents alike).

Usage:
    python -m scrapers.makita.analysis.chain_clustering
    python -m scrapers.makita.analysis.chain_clustering --top 9

This is the analysis behind the "Distribution Barbell" chart/report; rerun
it whenever output/makita/us/dealers.csv is refreshed to keep those numbers
current.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV = REPO_ROOT / "output" / "makita" / "us" / "dealers.csv"

# Ordered chain patterns: dealer names are tested top-to-bottom and the
# first match wins. Add new chains here as they show up in the long tail.
CHAIN_PATTERNS: list[tuple[str, str]] = [
    ("The Home Depot", r"\bHOME\s*DEPOT\b"),
    ("Tractor Supply Co.", r"\bTRACTOR SUPPLY\b"),
    ("White Cap", r"\bWHITE\s*CAP\b"),
    ("SiteOne Landscape Supply", r"\bSITEONE\b"),
    ("Platt Electric", r"\bPLATT ELECTRIC\b"),
    ("SouthernCarlson", r"\bSOUTHERN\s*CARLSON\b"),
    ("Fastenal", r"\bFASTENAL\b"),
    ("Rockler Woodworking", r"\bROCKLER\b"),
    ("HD Supply", r"\bHD SUPPLY\b"),
]

OTHER_LABEL = "All Other Dealers"


def classify(name: str) -> str:
    upper = name.upper()
    for label, pattern in CHAIN_PATTERNS:
        if re.search(pattern, upper):
            return label
    return OTHER_LABEL


def normalize_for_independent_count(name: str) -> str:
    """Collapse store-number suffixes so multi-location independents/regional
    chains inside the "All Other" bucket aren't double-counted as distinct
    banners (e.g. "MAC'S HARDWARE #3" and "MAC'S HARDWARE" -> one banner)."""
    n = name.upper()
    n = re.sub(r"#\s*\d+", "", n)
    n = re.sub(r"[.,\-]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def summarize(rows: list[dict], top_n: int = 9) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[classify(row["name"])].append(row)

    ranked = sorted(
        ((label, recs) for label, recs in buckets.items() if label != OTHER_LABEL),
        key=lambda item: len(item[1]),
        reverse=True,
    )

    total = len(rows)
    summary = []
    kept_labels = set()
    for label, recs in ranked[:top_n]:
        kept_labels.add(label)
        summary.append(_row_summary(label, recs, total))

    other_recs = [r for r in rows if classify(r["name"]) not in kept_labels]
    if other_recs:
        row = _row_summary(OTHER_LABEL, other_recs, total)
        banner_names = {normalize_for_independent_count(r["name"]) for r in other_recs}
        single_loc = sum(
            1
            for name, count in Counter(
                normalize_for_independent_count(r["name"]) for r in other_recs
            ).items()
            if count == 1
        )
        row["distinct_banners"] = len(banner_names)
        row["single_location_banners"] = single_loc
        summary.append(row)

    return summary


def _row_summary(label: str, recs: list[dict], total: int) -> dict:
    states = len({r["region"] for r in recs if r["region"]})
    pro_center = sum(1 for r in recs if "Pro Center" in (r["dealer_type"] or "")) / len(recs) * 100
    ope = sum(1 for r in recs if "Outdoor Power" in (r["extra_info"] or "")) / len(recs) * 100
    rental = sum(
        1
        for r in recs
        if "Rental" in (r["dealer_type"] or "") or "Rental" in (r["extra_info"] or "")
    ) / len(recs) * 100
    return {
        "chain": label,
        "locations": len(recs),
        "share_pct": round(len(recs) / total * 100, 1),
        "states_territories": states,
        "pro_center_pct": round(pro_center, 1),
        "ope_pct": round(ope, 1),
        "rental_pct": round(rental, 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to dealers.csv")
    parser.add_argument("--top", type=int, default=9, help="Number of named chains to break out")
    args = parser.parse_args(argv)

    with args.csv.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    summary = summarize(rows, top_n=args.top)

    header = f"{'Chain':28s} {'Count':>6s} {'Share':>7s} {'States':>7s} {'ProCtr%':>8s} {'OPE%':>6s} {'Rental%':>8s}"
    print(header)
    print("-" * len(header))
    for row in summary:
        print(
            f"{row['chain']:28s} {row['locations']:6d} {row['share_pct']:6.1f}% "
            f"{row['states_territories']:7d} {row['pro_center_pct']:7.1f}% "
            f"{row['ope_pct']:5.1f}% {row['rental_pct']:7.1f}%"
        )

    other = summary[-1]
    if "distinct_banners" in other:
        print(
            f"\n'{OTHER_LABEL}' spans {other['distinct_banners']} distinct banners, "
            f"{other['single_location_banners']} of them single-location "
            f"({other['single_location_banners'] / other['distinct_banners'] * 100:.1f}%)."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
