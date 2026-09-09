# Cap-IQ Benchmarking Project

## Bosch Professional dealer scraper

`bosch_dealers_scraper` scrapes the dealer/store locator at
https://www.bosch-professional.com/de/de/dealers/.

That page is a JavaScript widget with no data in the static HTML. Instead of
driving a browser, this scraper calls the same JSON API the widget itself
uses once a visitor searches a location:

```
POST https://www.bosch-professional.com/<market>/dealers/retailers/offline
Content-Type: application/x-www-form-urlencoded
latitude=<float>&longitude=<float>&radius=<meters>
```

A single query only returns dealers near one coordinate (and the backend
caps how many it returns), so covering a whole country means tiling it with
many overlapping searches and de-duplicating by dealer id — the
`--country-scan` mode below does this automatically.

### Install

```bash
pip install -r requirements.txt
```

### Usage

Search near a coordinate:

```bash
python -m bosch_dealers_scraper --lat 52.52 --lon 13.405 --radius-km 50 \
    --output dealers_berlin.csv
```

Search near a free-text location (geocoded via OpenStreetMap Nominatim —
pass `--user-agent` identifying yourself, per Nominatim's usage policy):

```bash
python -m bosch_dealers_scraper --location "10115 Berlin" --radius-km 25 \
    --user-agent "my-project/1.0 (me@example.com)" --output dealers.csv
```

Scan an entire country (default bounding box is Germany) and de-duplicate:

```bash
python -m bosch_dealers_scraper --country-scan --output dealers_de.csv
```

`--country` is a shortcut that sets both `--market` and `--bbox` for a known
country — currently `de` (Germany), `fr` (France), `gb` (UK), and `pl` (Poland):

```bash
python -m bosch_dealers_scraper --country-scan --country fr --output dealers_fr.csv
```

Any other market (Austria, Switzerland, UK, ...) works the same way via
`--market` + `--bbox` directly (see `robots.txt`'s sitemap list for every
market Bosch Professional runs, e.g. `at/de`, `ch/de`, `gb/en`):

```bash
python -m bosch_dealers_scraper --country-scan --market at/de \
    --bbox 46.3,9.5,49.1,17.2 --output dealers_at.csv
```

`--market`/`--bbox` always override `--country`'s preset if both are given.

Run `python -m bosch_dealers_scraper --help` for every option (output
format, request delay/retries, custom grid spacing, etc.).

### Output

CSV (default) or JSON with one row per dealer: id, name, website, full
address, phone/email/fax, coordinates, distance from the query point,
retailer type, premium/expert/flagship flags, delivery types, payment
methods, opening hours, and which query found it.

### Notes

- The scraper is polite by default: one request per second (`--delay`),
  retries with backoff on failure, and it only hits the endpoints the site's
  own `robots.txt` allows.
- `--country-scan`'s default 120 km grid spacing paired with a 100 km search
  radius overlaps enough for thorough coverage of Germany in practice, but
  it's a heuristic, not a guarantee — tighten `--spacing-km` /
  `--scan-radius-km` for denser coverage if completeness matters more than
  request count.

### Tests

```bash
python -m unittest discover -s tests -v
```
