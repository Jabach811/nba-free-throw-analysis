import unittest

from nba_ft.team_pipeline import enrich_schedule_context, validate_game


class TeamEndToEndTests(unittest.TestCase):
    def test_validates_player_and_team_attempts(self):
        rows = [{"player_id":"1"},{"player_id":"1"},{"player_id":"2"}]
        result = validate_game("g", rows, {"1":2,"2":1})
        self.assertTrue(result["passed"])
        self.assertEqual(result["team_actual"], 3)

    def test_enriches_rest_and_game_number(self):
        rows = [
            {"game_id":"a","date":"2025-10-20"},
            {"game_id":"b","date":"2025-10-21"},
        ]
        enriched = enrich_schedule_context(rows)
        self.assertEqual(enriched[1]["days_rest"], 0)
        self.assertTrue(enriched[1]["back_to_back"])
        self.assertEqual(enriched[1]["team_game_number"], 2)


if __name__ == "__main__":
    unittest.main()
