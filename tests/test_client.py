import unittest
from unittest.mock import MagicMock

from bosch_dealers_scraper.client import BoschDealerClient, DealerLocatorError


def _make_response(status_code=200, json_body=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_body or {}
    return response


class BoschDealerClientTests(unittest.TestCase):
    def test_search_offline_dealers_posts_expected_payload(self):
        session = MagicMock()
        session.post.return_value = _make_response(
            200, {"results": [{"dealer": {"id": "A1"}}], "defaultFilters": [], "filterCategories": []}
        )
        client = BoschDealerClient(session=session, request_delay=0)

        result = client.search_offline_dealers(52.52, 13.405, radius_m=50_000)

        self.assertEqual(len(result.results), 1)
        session.post.assert_called_once()
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], client.offline_api_url)
        self.assertEqual(
            kwargs["data"], {"latitude": 52.52, "longitude": 13.405, "radius": 50_000}
        )

    def test_retries_then_raises_on_persistent_failure(self):
        session = MagicMock()
        session.post.return_value = _make_response(500, {})
        client = BoschDealerClient(session=session, request_delay=0, max_retries=2, retry_backoff=0)

        with self.assertRaises(DealerLocatorError):
            client.search_offline_dealers(0, 0)

        self.assertEqual(session.post.call_count, 2)

    def test_market_builds_expected_urls(self):
        client = BoschDealerClient(market="at/de", session=MagicMock(), request_delay=0)
        self.assertEqual(
            client.offline_api_url,
            "https://www.bosch-professional.com/at/de/dealers/retailers/offline",
        )
        self.assertEqual(
            client.dealers_page_url, "https://www.bosch-professional.com/at/de/dealers/"
        )


if __name__ == "__main__":
    unittest.main()
