# DeWalt store-locator scraper

Scrapes dealer/retailer locations from DeWalt's official "find a retailer"
pages (e.g. https://www.dewalt.de/de-de/einzelhaendler-finden) without
driving a browser.

## How it works

DeWalt's country storefronts are all built on the same Next.js platform.
The store-locator page on each one calls a same-origin API route,
`POST https://<domain>/api/store-locator`, with a small JSON body and gets
back a page of dealer records plus a `next` cursor. This scraper calls that
same API route directly:

- With no `coordinates` in the request, the API returns **every** location
  listed for the country implied by the `lang` field, paginated — so a full
  national dealer list needs no geocoding or postcode grid, just pagination.
- Locations are split into three categories the site itself uses: local
  retailers (`store-retailer`), online retailers (`online-retailer`), and
  service centers (`service-center`). By default the scraper fetches all
  three and deduplicates by dealer id.

This is inherently tied to DeWalt/Stanley Black & Decker's current
storefront implementation. If they change it, `client.py` (the part that
builds the request/pagination) is the only piece that should need updating.

## Usage

```bash
pip install -r requirements.txt

# Every German dealer, retailer and service center -> output/dewalt_de.csv
python -m scrapers.dewalt.cli --country DE

# Just US online retailers, as JSON
python -m scrapers.dewalt.cli --country US --purpose online-retailer --format json
```

Run `python -m scrapers.dewalt.cli --help` for all options (output path,
page size, delay between requests, verbose logging).

## Adding a country

`countries.py` maps a short code to the storefront `domain` and the `lang`
value that storefront expects. To add one:

1. Open that country's find-a-retailer page in a browser with devtools open.
2. Trigger a search (or just let the page load) and find the `POST` request
   to `/api/store-locator`.
3. Copy the request's host as `domain`, and the `"lang"` field from its JSON
   body as `lang`, into a new `Country(...)` entry.

No other code changes are needed — `DE`, `US` and `FR` are already
configured as examples.

## Output columns

One row per unique dealer id: `id`, `name`, `source_purpose`,
`purpose_codes`, `brands`, `premium`, `is_online_only`, `is_head_quarter`,
`market_or_country`, `address1`, `address2`, `city`, `state`,
`postal_code`, `latitude`, `longitude`, `phone`, `email`, `website`,
`organization_name`, `google_rating`, `google_reviews_total`,
`created_at`, `updated_at`.
