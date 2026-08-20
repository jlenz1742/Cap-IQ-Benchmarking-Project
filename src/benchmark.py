#!/usr/bin/env python3
"""
Turn the tidy income-statement CSV (from normalize_output.py) into
industry benchmark stats: for each line item, express it as a % of
Total Revenue per company/year, then summarize those margins by
Industry and Year (mean, median, p25, p75, count).

Usage:
    python src/benchmark.py \
        --tidy output/income_statement_tidy.csv \
        --out output/industry_benchmarks.csv
"""
import argparse
from pathlib import Path

import pandas as pd

REVENUE_LABEL = "Total Revenue"


def compute_margins(tidy: pd.DataFrame) -> pd.DataFrame:
    tidy = tidy.copy()
    tidy["Value"] = pd.to_numeric(tidy["Value"], errors="coerce")

    revenue = (
        tidy[tidy["LineItem"] == REVENUE_LABEL]
        [["CompanyName", "Year", "Value"]]
        .rename(columns={"Value": "Revenue"})
    )

    merged = tidy.merge(revenue, on=["CompanyName", "Year"], how="left")
    merged["Margin"] = merged["Value"] / merged["Revenue"]
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
