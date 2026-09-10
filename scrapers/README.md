# Scrapers

## `festool_dealer_scraper.py`

Pulls the full list of US Festool dealers.

Festool's ["Find a Dealer"](https://www.festoolusa.com/dealer) page embeds a
store-locator widget from **Locally.com**. That widget calls a public JSON
endpoint (`https://festool.locally.com/stores/conversion_data`) with a
lat/lng + radius to get dealers near a point — no login or API key needed,
it's the same request the map widget makes from any visitor's browser.

The script queries a grid of overlapping regions covering the whole US
(continental US + Alaska + Hawaii) and de-duplicates dealers by store id, so
the result is complete even though a single nationwide query already turns
out to return every dealer un-truncated (verified by cross-checking against
independent regional queries — same per-state counts either way).

### Usage

```bash
pip install requests   # if not already available
python3 festool_dealer_scraper.py -o festool_dealers_us.csv
```

Options:
- `-o/--output` — CSV path (default `festool_dealers_us.csv`)
- `--json` — also write a JSON copy
- `--delay` — seconds between requests (default `0.75`, be polite)

### Output columns

`id, name, address, city, state, zip, phone, lat, lng, is_claimed, timezone,
slug, dealer_page_url`

As of the last run this returns **1,819 dealers** across all 50 states + DC.

### Notes

- This only reads the same public data the dealer locator already serves to
  every site visitor — it doesn't bypass authentication, pagination limits,
  or rate limiting designed to protect non-public data.
- The `company_id`/`dealers_company_id` (`261617`) is Festool's id in
  Locally.com's system; other brands using the same widget would have a
  different id, discoverable the same way (view-source the brand's dealer
  locator page, look for `lcly_config_*`).
