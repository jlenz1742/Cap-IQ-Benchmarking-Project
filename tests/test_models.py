import unittest

from bosch_dealers_scraper.models import flatten_dealer

SAMPLE_HIT = {
    "dealer": {
        "id": "C000161",
        "name": "Meesenburg GmbH - Sicherheit & Service",
        "website": "http://www.meesenburg.com",
        "address": {
            "street": "Köpenicker Straße 26-29",
            "zip": "10997",
            "city": "Berlin",
            "country": "DE",
            "latitude": 52.507218,
            "longitude": 13.429363,
            "phone": "+49302576202460",
            "email": "",
            "fax": "+49 30 257620-1000",
        },
        "benefits": ["company.b2b", "misc.waitingarea"],
        "shopHours": [
            {
                "language": "de",
                "description": "Mo: |07:00 - 16:30 Uhr<br/>Di: ||07:00 - 16:30 Uhr<br/>Sa: ||Geschlossen",
            }
        ],
        "serviceHours": [],
        "retailerTypes": ["TRADITIONAL_TRADE", "regular_dealer"],
        "premium": False,
        "expert": True,
        "premiumFlagship": True,
        "deliveryTypes": ["PICKUP", "EXPRESS", "NORMAL"],
        "paymentMethods": ["CASH", "EC_CARD", "INVOICE"],
        "openNow": False,
        "closesAt": None,
    },
    "rank": 50,
    "distance": 2176,
    "properties": {
        "regular-dealer": {"name": "regular-dealer"},
        "premium-partner": {"name": "Bosch Premium Partner"},
    },
    "services": [],
    "stock": None,
}


class FlattenDealerTests(unittest.TestCase):
    def test_flattens_core_fields(self):
        record = flatten_dealer(SAMPLE_HIT)
        self.assertEqual(record["dealer_id"], "C000161")
        self.assertEqual(record["name"], "Meesenburg GmbH - Sicherheit & Service")
        self.assertEqual(record["zip"], "10997")
        self.assertEqual(record["city"], "Berlin")
        self.assertEqual(record["distance_m"], 2176)
        self.assertEqual(record["retailer_types"], "TRADITIONAL_TRADE; regular_dealer")
        self.assertIn("premium-partner", record["badges"])
        self.assertIn("regular-dealer", record["badges"])

    def test_cleans_opening_hours(self):
        record = flatten_dealer(SAMPLE_HIT)
        self.assertNotIn("<br", record["shop_hours"])
        self.assertIn("Mo:", record["shop_hours"])
        self.assertIn("Geschlossen", record["shop_hours"])

    def test_handles_missing_optional_fields(self):
        record = flatten_dealer({"dealer": {"id": "X1"}, "rank": 1, "distance": 0})
        self.assertEqual(record["dealer_id"], "X1")
        self.assertEqual(record["shop_hours"], "")
        self.assertEqual(record["retailer_types"], "")


if __name__ == "__main__":
    unittest.main()
