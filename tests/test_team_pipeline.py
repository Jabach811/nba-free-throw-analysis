import unittest

from nba_ft.team_pipeline import discover_team_games, game_context, classify_team_game


class TeamDiscoveryTests(unittest.TestCase):
    def test_discovers_supported_segments_and_excludes_preseason(self):
        schedules = [
            {"events":[{"id":"pre","seasonType":{"type":1,"name":"Preseason"}}]},
            {"events":[{"id":"reg","date":"2025-10-20","seasonType":{"type":2,"name":"Regular Season"}}]},
            {"events":[{"id":"pin","seasonType":{"type":5,"name":"Play-In Season"}}]},
            {"events":[{"id":"po","seasonType":{"type":3,"name":"Postseason"}}]},
        ]
        self.assertEqual(set(discover_team_games(schedules)), {"reg", "pin", "po"})

    def test_game_context_tracks_home_and_opponent(self):
        summary = {"header":{"competitions":[{"competitors":[
            {"id":"9","homeAway":"away","team":{"id":"9","abbreviation":"GS"}},
            {"id":"7","homeAway":"home","team":{"id":"7","abbreviation":"DEN"}},
        ]}]}}
        context = game_context(summary, "9")
        self.assertEqual(context["venue"], "away")
        self.assertEqual(context["opponent"], "DEN")


class TeamClassificationTests(unittest.TestCase):
    def test_accepts_decimal_seconds_clock_for_clutch(self):
        summary = {"plays":[{"id":"1","sequenceNumber":"1","type":{"text":"Technical Free Throw"},"text":"Stephen Curry makes technical free throw","period":{"number":4},"clock":{"displayValue":"39.1"},"team":{"id":"9"},"awayScore":99,"homeScore":100,"participants":[{"athlete":{"id":"3975"}}]}]}
        rows = classify_team_game("g", "Regular Season", summary, "9", {"3975":"Stephen Curry"}, {"venue":"away"})
        self.assertTrue(rows[0]["clutch"])

    def test_classifies_two_players_and_score_context(self):
        summary = {"plays":[
            {"id":"1","sequenceNumber":"1","type":{"text":"Shooting Foul"},"text":"Foul","period":{"number":4},"clock":{"displayValue":"4:00"},"team":{"id":"7"},"awayScore":98,"homeScore":100},
            {"id":"2","sequenceNumber":"2","type":{"text":"Free Throw - 1 of 2"},"text":"Stephen Curry misses free throw 1 of 2","period":{"number":4},"clock":{"displayValue":"4:00"},"team":{"id":"9"},"awayScore":98,"homeScore":100,"participants":[{"athlete":{"id":"3975"}}]},
            {"id":"3","sequenceNumber":"3","type":{"text":"Free Throw - 2 of 2"},"text":"Stephen Curry makes free throw 2 of 2","period":{"number":4},"clock":{"displayValue":"4:00"},"team":{"id":"9"},"awayScore":99,"homeScore":100,"participants":[{"athlete":{"id":"3975"}}]},
            {"id":"4","sequenceNumber":"4","type":{"text":"Technical Free Throw"},"text":"Jimmy Butler makes technical free throw","period":{"number":4},"clock":{"displayValue":"3:00"},"team":{"id":"9"},"awayScore":100,"homeScore":100,"participants":[{"athlete":{"id":"6430"}}]},
        ]}
        players = {"3975":"Stephen Curry", "6430":"Jimmy Butler III"}
        rows = classify_team_game("g", "Regular Season", summary, "9", players, {"venue":"away","opponent":"DEN","date":"2025-10-20"})
        self.assertEqual([r["player_name"] for r in rows], ["Stephen Curry", "Stephen Curry", "Jimmy Butler III"])
        self.assertEqual(rows[1]["previous_result"], "missed")
        self.assertEqual(rows[1]["score_margin_before"], -2)
        self.assertTrue(rows[1]["clutch"])
        self.assertEqual(rows[2]["trip_type"], "technical")


if __name__ == "__main__":
    unittest.main()
