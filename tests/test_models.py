import unittest

from nba_ft.models import segment_from_game_id


class SegmentTests(unittest.TestCase):
    def test_maps_supported_game_types(self):
        self.assertEqual(segment_from_game_id("0022500001"), "Regular Season")
        self.assertEqual(segment_from_game_id("0052500001"), "Play-In")
        self.assertEqual(segment_from_game_id("0042500001"), "Playoffs")

    def test_rejects_unsupported_game_type(self):
        with self.assertRaises(ValueError):
            segment_from_game_id("0012500001")


if __name__ == "__main__":
    unittest.main()
