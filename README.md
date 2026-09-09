# Cap-IQ-Benchmarking-Project

## Makita dealer scraper

`scrapers/makita/` scrapes Makita's country "Händlersuche" (dealer locator)
sites, one country at a time.

### How it works

Each Makita country site embeds a third-party "dealerlocator" widget backed
by a single JSON endpoint: `/crm/front/dealerlocator/dealerlocator_ajax.asp`.
Requesting it with `show_all_dealers=true` (the mode the site's own results
table uses) returns the complete dealer list for that country in one call —
no pagination, postcode grid search, or browser automation required.

Per-country widget IDs (`dealerlocator_id`, `query_id`,
`countries_for_results`, `extra_search_condition`) live in
`scrapers/makita/countries.py`. Only Germany (`de`) is configured so far;
add more countries there by viewing source on that country's dealer locator
page and copying the corresponding `dealerlocatorJS.edit_*` values.

### Usage

```bash
pip install -r requirements.txt
python -m scrapers.makita.scrape --country de
```

Writes `output/makita/de/dealers.csv` by default (override with `--out`).
Add `--json-out <path>` to also dump the raw records as JSON.

Each row includes: name, dealer type, address (street/postcode/city),
phone, fax, email, website, lat/lng, and the geocoded address string
Makita's own system resolved for that dealer.
