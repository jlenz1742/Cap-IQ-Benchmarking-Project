"""Scraper for DeWalt's official "find a retailer" store locator.

DeWalt's country storefronts (dewalt.de, dewalt.com, dewalt.fr, ...) are all
built on the same Next.js platform and expose an identical JSON API route,
``POST /api/store-locator``, that the store-locator page calls in the
browser. This package talks to that API directly instead of driving a
browser, which makes it fast and easy to extend to additional countries --
see ``countries.py`` for how to add one.
"""
