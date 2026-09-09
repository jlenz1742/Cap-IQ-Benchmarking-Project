import unittest

from bosch_dealers_scraper.grid import generate_grid


class GenerateGridTests(unittest.TestCase):
    def test_covers_whole_bbox(self):
        bbox = (47.2, 5.5, 55.1, 15.5)
        points = list(generate_grid(bbox, spacing_km=120))
        self.assertGreater(len(points), 1)
        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        self.assertGreaterEqual(min(lats), bbox[0])
        self.assertLessEqual(max(lats), bbox[2] + 1e-6)
        self.assertGreaterEqual(min(lons), bbox[1])
        self.assertLessEqual(max(lons), bbox[3] + 1e-6)

    def test_smaller_spacing_yields_more_points(self):
        bbox = (47.2, 5.5, 55.1, 15.5)
        coarse = list(generate_grid(bbox, spacing_km=200))
        fine = list(generate_grid(bbox, spacing_km=50))
        self.assertLess(len(coarse), len(fine))

    def test_invalid_bbox_raises(self):
        with self.assertRaises(ValueError):
            list(generate_grid((10, 10, 5, 20), spacing_km=100))

    def test_invalid_spacing_raises(self):
        with self.assertRaises(ValueError):
            list(generate_grid((0, 0, 1, 1), spacing_km=0))


if __name__ == "__main__":
    unittest.main()
