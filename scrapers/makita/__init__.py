"""Scrapers for Makita's dealer locator ("Händlersuche") sites.

Makita's country sites (makita.de, and presumably other makita.<tld>
domains) are backed by a third-party "dealerlocator" widget that exposes a
single JSON endpoint per site: ``/crm/front/dealerlocator/dealerlocator_ajax.asp``.
Passing ``show_all_dealers=true`` returns the full dealer list for the
configured country in one request, so no pagination or geo-grid searching
is needed.

See ``countries.py`` for the per-country widget configuration and
``client.py`` for the HTTP client that talks to the endpoint.
"""
