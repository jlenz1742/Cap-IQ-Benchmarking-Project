"""Per-country configuration for Makita's dealer locator widget.

Each Makita country site embeds the "dealerlocator" widget with its own
settings (visible in the page's inline <script> block as calls like
``dealerlocatorJS.edit_dealerlocator_id('2547')``). To add a new country,
load that country's Händlersuche / dealer-locator page, view source, and
copy the corresponding values into a new ``CountryConfig`` entry below.

Values for Germany were read from:
https://www.makita.de/h%C3%A4ndlersuche.html
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryConfig:
    """Widget configuration needed to query one Makita country site."""

    code: str
    """Short identifier used on the CLI, e.g. "de"."""

    name: str
    """Human-readable country name."""

    base_url: str
    """Scheme + host of the Makita site, e.g. "https://www.makita.de"."""

    dealerlocator_id: str
    """``dealerlocatorJS.edit_dealerlocator_id(...)`` value from the page."""

    query_id: str
    """``dealerlocatorJS.edit_query_id(...)`` value from the page."""

    countries_for_results: str
    """``dealerlocatorJS.edit_countries_for_results(...)`` value."""

    extra_search_condition: str
    """``dealerlocatorJS.edit_extra_search_condition(...)`` value."""


COUNTRIES: dict[str, CountryConfig] = {
    "de": CountryConfig(
        code="de",
        name="Germany",
        base_url="https://www.makita.de",
        dealerlocator_id="2547",
        query_id="1",
        countries_for_results="DE",
        extra_search_condition="GERMANY",
    ),
}


def get_country(code: str) -> CountryConfig:
    try:
        return COUNTRIES[code.lower()]
    except KeyError as exc:
        available = ", ".join(sorted(COUNTRIES))
        raise ValueError(
            f"Unknown country code {code!r}. Available: {available}"
        ) from exc
