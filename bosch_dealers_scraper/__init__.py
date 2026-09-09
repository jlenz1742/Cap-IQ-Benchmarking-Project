"""Scraper for the Bosch Professional dealer locator.

See ``bosch_dealers_scraper.cli`` for the command line entry point and
``bosch_dealers_scraper.client`` for the underlying HTTP client that talks
to the dealer-locator API used by
https://www.bosch-professional.com/de/de/dealers/.
"""

from .client import BoschDealerClient, DealerLocatorError
from .models import flatten_dealer

__all__ = ["BoschDealerClient", "DealerLocatorError", "flatten_dealer"]
