import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from bosch_dealers_scraper import cli


class CountryPresetResolutionTests(unittest.TestCase):
    """--country should set market/bbox, but explicit --market/--bbox win."""

    def _run(self, argv):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        self.addCleanup(os.remove, path)
        with patch.object(cli, "BoschDealerClient") as client_cls, patch.object(
            cli, "run_single_search", return_value=[]
        ) as run_single, patch.object(cli, "run_country_scan", return_value=[]) as run_scan:
            client_cls.return_value = MagicMock()
            cli.main(argv + ["--output", path])
            return client_cls, run_single, run_scan

    def test_country_fr_sets_market_and_bbox(self):
        client_cls, _, run_scan = self._run(["--country-scan", "--country", "fr"])
        self.assertEqual(client_cls.call_args.kwargs["market"], "fr/fr")
        used_bbox = run_scan.call_args.args[1]
        from bosch_dealers_scraper.grid import FRANCE_BBOX

        self.assertEqual(used_bbox, FRANCE_BBOX)

    def test_explicit_market_overrides_country_preset(self):
        client_cls, _, _ = self._run(
            ["--country-scan", "--country", "fr", "--market", "at/de"]
        )
        self.assertEqual(client_cls.call_args.kwargs["market"], "at/de")

    def test_no_country_defaults_to_germany(self):
        client_cls, _, run_scan = self._run(["--country-scan"])
        self.assertEqual(client_cls.call_args.kwargs["market"], "de/de")
        used_bbox = run_scan.call_args.args[1]
        from bosch_dealers_scraper.grid import GERMANY_BBOX

        self.assertEqual(used_bbox, GERMANY_BBOX)


if __name__ == "__main__":
    unittest.main()
