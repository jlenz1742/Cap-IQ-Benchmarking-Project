"""Registry of DeWalt country storefronts supported by the scraper.

Every DeWalt country site is a separate deployment of the same Next.js
storefront, and every one of them exposes the same ``/api/store-locator``
API route used by that site's own "find a retailer" page. To scrape a new
country, you only need its domain and the locale string ("lang") that site
sends in its own store-locator requests -- no new scraping logic required.

How to find those two values for a country that isn't listed yet:
  1. Open that country's "find a retailer" page in a browser
     (e.g. https://www.dewalt.<tld>/<locale>/find-a-retailer or whatever
     that site calls it) with devtools' Network tab open.
  2. Run any search (or just let the page load) and find the POST request
     to ``/api/store-locator``.
  3. The request's host is the ``domain`` below; the ``"lang"`` field in its
     JSON body is the ``lang`` below.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str  # short code used to select this country on the CLI
    domain: str  # storefront domain that hosts /api/store-locator
    lang: str  # locale string this storefront expects in request bodies
    name: str  # human-readable name, for logging/output only


COUNTRIES = {
    "DE": Country(code="DE", domain="www.dewalt.de", lang="de-de", name="Germany"),
    "US": Country(code="US", domain="www.dewalt.com", lang="en-us", name="United States"),
    "FR": Country(code="FR", domain="www.dewalt.fr", lang="fr-fr", name="France"),
}
