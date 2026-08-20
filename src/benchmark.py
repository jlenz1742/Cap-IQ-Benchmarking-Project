#!/usr/bin/env python3
"""
Turn the tidy income-statement CSV (from normalize_output.py) into
industry benchmark stats: for each dollar line item, express it as a %
of Total Revenue per company/year; for line items that are already a
ratio/multiple (see RATIO_LINE_ITEMS), use the value as-is instead of
dividing by revenue. Then summarize by Industry and Year (mean, median,
p25, p75, count).

Usage:
    python src/benchmark.py \
        --tidy output/income_statement_tidy.csv \
        --out output/industry_benchmarks.csv
"""
import argparse
from pathlib import Path

import pandas as pd

REVENUE_LABEL = "Total Revenue"

# Line items that are already a ratio/multiple, not a dollar amount --
# these should NOT be divided by revenue. Add to this set as needed
# when adding non-dollar line items to config/mnemonics.csv.
RATIO_LINE_ITEMS = {"EV / EBITDA"}


def compute_margins(tidy: pd.DataFrame) -> pd.DataFrame:
    tidy = tidy.copy()
    tidy["Value"] = pd.to_numeric(tidy["Value"], errors="coerce")

    revenue = (
        tidy[tidy["LineItem"] == REVENUE_LABEL]
        [["CompanyName", "Year", "Value"]]
        .rename(columns={"Value": "Revenue"})
    )

    merged = tidy.merge(revenue, on=["CompanyName", "Year"], how="left")
    is_ratio = merged["LineItem"].isin(RATIO_LINE_ITEMS)
    merged["Margin"] = merged["Value"] / merged["Revenue"]
    merged.loc[is_ratio, "Margin"] = merged.loc[is_ratio, "Value"]
    return merged


def summarize(merged: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        merged.groupby(["Industry", "Year", "LineItem"])["Margin"]
        .agg(
            n="count",
            mean="mean",
            median="median",
            p25=lambda s: s.quantile(0.25),
            p75=lambda s: s.quantile(0.75),
        )
        .reset_index()
    )
    return grouped.sort_values(["Industry", "Year", "LineItem"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tidy", default="output/income_statement_tidy.csv")
    ap.add_argument("--out", default="output/industry_benchmarks.csv")
    ap.add_argument("--margins-out", default="output/company_margins.csv",
                     help="also write the per-company, per-year margin detail")
    args = ap.parse_args()

    tidy = pd.read_csv(args.tidy)
    merged = compute_margins(tidy)
    benchmarks = summarize(merged)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    benchmarks.to_csv(out_path, index=False)

    margins_path = Path(args.margins_out)
    merged[["CompanyName", "Industry", "Year", "LineItem", "Value", "Revenue", "Margin"]].to_csv(
        margins_path, index=False
    )

    print(f"Wrote {len(benchmarks)} industry/year/line-item benchmark rows to {out_path}")
    print(f"Wrote per-company margin detail to {margins_path}")


if __name__ == "__main__":
    main()
