#!/usr/bin/env python3
"""
Generate an Excel workbook wired up with S&P Capital IQ Excel Plug-in
formulas (=CIQ(...)) for a list of companies and income-statement line
items.

This script does NOT talk to Capital IQ itself -- it has no login and
no network access to S&P's platform. It only writes formulas. You open
the resulting .xlsx in Excel on a machine where the Capital IQ
Office/Excel Add-in is installed and you are logged in, then use the
Add-in's "Refresh Data" (or Ctrl+Alt+F9 / the CapIQ ribbon's refresh
button) to pull live values into the cells.

Usage:
    python src/generate_template.py \
        --companies companies.csv \
        --mnemonics config/mnemonics.csv \
        --years 5 \
        --out output/CapIQ_Income_Statement_Template.xlsx

companies.csv columns: CompanyName, Identifier, Industry
    - Identifier should be whatever the CIQ() formula can resolve:
      a ticker (e.g. "MSFT"), CUSIP, ISIN, SEDOL, or a Capital IQ
      Company ID (e.g. "IQ123456"). Plain free-text company names are
      NOT reliably resolved by the formula engine -- use the CapIQ
      ribbon's company search/lookup to find the right identifier for
      each name and paste it into this column. If Identifier is left
      blank, CompanyName is used as a best-effort fallback so you can
      see the formulas and fix identifiers directly in Excel.

config/mnemonics.csv columns: Label, Mnemonic
    - CIQ mnemonics for the line items you want. The defaults shipped
      here (IQ_TOTAL_REV, IQ_COGS, IQ_GP, IQ_SGA, IQ_EBITDA, ...) are
      the standard Capital IQ income-statement mnemonics, but exact
      availability/naming can vary by subscription and template
      version -- verify against your own Formula Builder in the CapIQ
      ribbon and edit this file if any come back as #N/A.
"""
import argparse
import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
BOLD = Font(bold=True)


def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_workbook(companies, mnemonics, years):
    wb = Workbook()

    # --- Config sheet: mnemonics, editable without touching formulas ---
    cfg = wb.active
    cfg.title = "Config"
    cfg.append(["Label", "Mnemonic"])
    for cell in cfg[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for row in mnemonics:
        cfg.append([row["Label"], row["Mnemonic"]])
    cfg.column_dimensions["A"].width = 28
    cfg.column_dimensions["B"].width = 20

    # --- Companies sheet: identifiers you fill in via CapIQ lookup ---
    comp = wb.create_sheet("Companies")
    comp.append(["CompanyName", "Identifier", "Industry"])
    for cell in comp[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for row in companies:
        comp.append([
            row.get("CompanyName", ""),
            row.get("Identifier") or row.get("CompanyName", ""),
            row.get("Industry", ""),
        ])
    for col, width in zip("ABC", (30, 16, 22)):
        comp.column_dimensions[col].width = width

    # --- Income Statement sheet: one row per (company, line item) ---
    sheet = wb.create_sheet("Income Statement")
    year_tokens = ["IQ_FY"] + [f"IQ_FY-{i}" for i in range(1, years)]
    year_labels = ["FY (latest)"] + [f"FY-{i}" for i in range(1, years)]

    header = ["Company", "Identifier", "Industry", "Line Item", "Mnemonic"] + year_labels
    sheet.append(header)
    for cell in sheet[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    sheet.freeze_panes = "F2"

    n_items = len(mnemonics)
    company_start_row = 2
    for ci, crow in enumerate(companies):
        identifier = crow.get("Identifier") or crow.get("CompanyName", "")
        industry = crow.get("Industry", "")
        company_name = crow.get("CompanyName", "")
        for li, mrow in enumerate(mnemonics):
            r = company_start_row + ci * n_items + li
            sheet.cell(row=r, column=1, value=company_name)
            sheet.cell(row=r, column=2, value=identifier)
            sheet.cell(row=r, column=3, value=industry)
            sheet.cell(row=r, column=4, value=mrow["Label"])
            sheet.cell(row=r, column=5, value=mrow["Mnemonic"])
            id_cell = f"$B{r}"
            mnem_cell = f"$E{r}"
            for yi, token in enumerate(year_tokens):
                col = 6 + yi  # column F onward
                formula = f'=CIQ({id_cell},{mnem_cell},"IQ_FY",{-yi if yi else 0})'
                sheet.cell(row=r, column=col, value=formula)
        if li == n_items - 1:
            # bold the company name's first row of each block for readability
            sheet.cell(row=company_start_row + ci * n_items, column=1).font = BOLD

    widths = {"A": 28, "B": 14, "C": 20, "D": 24, "E": 18}
    for col, width in widths.items():
        sheet.column_dimensions[col].width = width
    for yi in range(len(year_tokens)):
        sheet.column_dimensions[get_column_letter(6 + yi)].width = 14

    # --- Notes sheet ---
    notes = wb.create_sheet("Notes")
    notes_text = [
        "How to use this workbook",
        "",
        "1. Fill in / correct the 'Identifier' column on the Companies sheet"
        " using tickers, CUSIP/ISIN, or Capital IQ Company IDs. Use the CapIQ"
        " ribbon's company search to resolve a plain company name to a valid"
        " identifier if you're not sure.",
        "2. Open the 'Income Statement' sheet. Cells are formulas of the form"
        ' =CIQ(Identifier, Mnemonic, "IQ_FY", offset). They will show #N/A or'
        " blank until refreshed.",
        "3. With the Capital IQ Excel Add-in installed and you logged in, use"
        " the CapIQ ribbon's Refresh / Refresh All Data command (or Ctrl+Alt+F9,"
        " depending on your Add-in version) to pull live data into the sheet.",
        "4. If a mnemonic returns #N/A for your subscription/template version,"
        " open your Add-in's Formula Builder, find the correct mnemonic for that"
        " line item, and update it on the Config / Income Statement sheets"
        " (column E) -- the formula structure does not need to change.",
        "5. Save the refreshed workbook, then run"
        " src/normalize_output.py against it to produce a tidy CSV for"
        " benchmarking.",
        "",
        "Note on fiscal years: 'IQ_FY' / 'IQ_FY-1' etc. pull each company's own"
        " most recent reported fiscal year and prior years relative to it --"
        " companies with different fiscal year-ends will therefore have"
        " differently-dated columns even though they're aligned as 'FY', 'FY-1', ...",
    ]
    for i, line in enumerate(notes_text, start=1):
        notes.cell(row=i, column=1, value=line)
    notes.column_dimensions["A"].width = 100
    notes["A1"].font = Font(bold=True, size=13)

    return wb


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--companies", default="companies.csv")
    ap.add_argument("--mnemonics", default="config/mnemonics.csv")
    ap.add_argument("--years", type=int, default=5, help="number of fiscal years back to pull (default 5)")
    ap.add_argument("--out", default="output/CapIQ_Income_Statement_Template.xlsx")
    args = ap.parse_args()

    companies = read_csv_rows(args.companies)
    mnemonics = read_csv_rows(args.mnemonics)
    if not companies:
        raise SystemExit(f"No companies found in {args.companies}")
    if not mnemonics:
        raise SystemExit(f"No mnemonics found in {args.mnemonics}")

    wb = build_workbook(companies, mnemonics, args.years)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    print(f"Wrote {out_path} ({len(companies)} companies x {len(mnemonics)} line items x {args.years} years)")


if __name__ == "__main__":
    main()
