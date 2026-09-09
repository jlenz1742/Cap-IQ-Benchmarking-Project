# Cap-IQ-Benchmarking-Project

## Makita dealer scraper

`scrapers/makita/` scrapes Makita's country dealer-locator sites, one
country at a time, into a common CSV schema (see `Dealer` in
`scrapers/makita/client.py`).

### Germany (`de`)

makita.de's "Händlersuche" embeds a third-party "dealerlocator" widget
backed by a single JSON endpoint: `/crm/front/dealerlocator/dealerlocator_ajax.asp`.
Requesting it with `show_all_dealers=true` (the mode the site's own results
table uses) returns the complete dealer list for that country in one call —
no pagination, postcode grid search, or browser automation required.

Per-country widget IDs (`dealerlocator_id`, `query_id`,
`countries_for_results`, `extra_search_condition`) live in
`scrapers/makita/countries.py`. Add more `dealerlocator`-widget countries
there by viewing source on that country's dealer locator page and copying
the corresponding `dealerlocatorJS.edit_*` values.

### United States (`us`)

makitatools.com's "Buy Local" locator (`/products/buy-local`) is a
different, in-house tool (Leaflet map + `GeoSearch` JS) backed by a
geo-radius search API instead of a "give me everything" endpoint:

```
GET /api/getretailersbyretailertypewithinmiles?zip=&lat=<lat>&lon=<lon>&miles=200&retailerType=0
```

`retailerType=0` means "no type filter" (all dealer classes); 200 miles is
the widget's own max radius. `scrapers/makita/us.py` covers the country by
querying a grid of lat/lon points (contiguous US, Alaska, Hawaii, Puerto
Rico) spaced closely enough that adjacent 200-mile search circles overlap
with margin, then de-duplicates the results (the API returns no stable
dealer id, so dealers are de-duplicated by name + street + zip).

That site also serves its TLS leaf certificate without the intermediate
("Go Daddy Secure Certificate Authority - G2") CA that signs it — browsers
tolerate this via cached/AIA-fetched intermediates, but Python's `ssl`
module doesn't. `scrapers/makita/ssl_utils.py` works around it by trusting
that (public, standard) intermediate alongside the normal certifi trust
store, rather than disabling verification.

### Usage

```bash
pip install -r requirements.txt
python -m scrapers.makita.scrape --country de
python -m scrapers.makita.scrape --country us
```

Writes `output/makita/<country>/dealers.csv` by default (override with
`--out`). Add `--json-out <path>` to also dump the raw records as JSON.

Each row includes: name, dealer type, address (street/postcode/city,
region for US state), country, phone, fax, email, website, and lat/lng.
The German rows also carry the geocoded address string Makita's own system
resolved for that dealer.

Latest run: 2,388 dealers in Germany, 7,408 in the US.
