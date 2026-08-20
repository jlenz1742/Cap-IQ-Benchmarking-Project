# Cap IQ Benchmarking Project

Pulls income-statement data for a list of companies via the **S&P Capital
IQ Excel Plug-in** and turns it into topline / cost-structure benchmarks
by industry.

## Why it works this way

This environment has no Capital IQ login and no network access to S&P's
platform, and scripting/scraping the Capital IQ Pro website directly is
against S&P's terms of use. The supported way to bulk-extract data with a
standard Capital IQ subscription is the Excel Add-in's `=SPG(...)`
formulas, so the pipeline is split into a step that runs here (generating
formulas) and a step that has to run on your machine, in Excel, logged
into Capital IQ (actually pulling the data):

1. **`src/generate_template.py`** (runs anywhere) — takes your company
   list and a set of income-statement line items, and writes an `.xlsx`
   full of `=SPG(Identifier, Mnemonic, YearCell)` formulas, one column
   per fiscal year (e.g. `=SPG($B2,$E2,F$1)` where `F1` holds the text
   `FY2019`) -- the year comes from the column's own header cell rather
   than being hard-coded into the formula, so editing row 1 in Excel is
   enough to try a different year. No data yet — just formulas.
2. **You, in Excel** — open the workbook with the Capital IQ Add-in
   installed and logged in, fix up any company identifiers, and hit
   Refresh Data. The formulas resolve to real numbers. Save the file.
3. **`src/normalize_output.py`** (runs anywhere) — reads the refreshed
   workbook and reshapes it into a tidy CSV: one row per
   company/line-item/year.
4. **`src/benchmark.py`** (runs anywhere) — expresses every line item as
   a % of revenue per company/year, then aggregates those margins by
   industry and year (mean, median, p25, p75) for benchmarking.

## Quick start

```bash
pip install -r requirements.txt

# 1. Edit companies.csv with the companies you care about.
#    Identifier = ticker, CUSIP/ISIN, or Capital IQ Company ID.
#    If you only know company names, leave Identifier blank -- the
#    template will use the name as a placeholder you can fix in Excel
#    using the CapIQ ribbon's company search.

python src/generate_template.py --companies companies.csv
# (defaults to FY2019 through last year -- pass --start-year/--end-year to override)

# 2. Open output/CapIQ_Income_Statement_Template.xlsx in Excel,
#    fix identifiers if needed, Refresh Data via the CapIQ Add-in,
#    save the file.

python src/normalize_output.py --workbook output/CapIQ_Income_Statement_Template.xlsx
python src/benchmark.py
```

Outputs land in `output/`:
- `income_statement_tidy.csv` — raw values, long format
- `company_margins.csv` — each line item as % of revenue, per company/year
- `industry_benchmarks.csv` — margin percentiles by industry and year

## Customizing line items

Edit `config/mnemonics.csv` (Label, Mnemonic). The defaults are the
standard Capital IQ income-statement mnemonics (`IQ_TOTAL_REV`,
`IQ_COGS`, `IQ_GP`, `IQ_SGA`, `IQ_EBITDA`, ...), but exact mnemonic
availability can vary by subscription/template version. If a cell comes
back `#N/A` after refresh, look up the correct mnemonic in your Add-in's
Formula Builder and update it here — you don't need to touch the
generated formulas' structure, since the mnemonic is a cell reference.

## Notes / limitations

- Each Income Statement column is a fiscal year (`FY2019`, `FY2020`,
  ...) from `--start-year` through `--end-year` (default: 2019 through
  last calendar year, i.e. the most recently completed fiscal year --
  re-running the script with no flags automatically rolls the window
  forward by a year). A company that hasn't reported a given year yet
  will simply come back blank/`#N/A` for that column — expected, not a
  bug to chase.
- One extra column is appended after the full years for the current
  year's H1 (first half), using Capital IQ's own interim-period token
  (`FH12026`) -- but only once that half has actually closed (from July
  onward). Use `--no-h1` to skip it, or `--h1-year YYYY` to force a
  specific year.
- Formulas reference the year from their column's row-1 header cell
  (e.g. `F$1` holding `"FY2019"`) instead of a literal string, so you
  can retype a header cell in Excel to repoint a whole column without
  touching the formulas underneath it.
- This does not automate the Excel refresh step itself — CapIQ's terms
  require a logged-in, licensed user driving the Add-in, so step 2 stays
  manual (or could be scripted locally with `xlwings`/VBA on a machine
  that already has the Add-in and a valid session, which is out of scope
  for this repo).
