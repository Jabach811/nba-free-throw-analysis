import unittest

from nba_ft.stints import attach_workload, build_stints, game_elapsed


class StintTests(unittest.TestCase):
    def test_parses_decimal_seconds_clock_under_one_minute(self):
        self.assertEqual(game_elapsed(1, "39.1"), 680.9)

    def test_reconstructs_continuous_and_cumulative_workload(self):
        summary = {
            "boxscore":{"players":[
                {"team":{"id":"9"},"statistics":[{"athletes":[
                    {"starter":True,"athlete":{"id":"1","displayName":"Player One"}},
                    {"starter":False,"athlete":{"id":"2","displayName":"Player Two"}},
                ]}]}
            ]},
            "plays":[
                {"sequenceNumber":"10","period":{"number":1},"clock":{"displayValue":"8:00"},"team":{"id":"9"},"type":{"text":"Substitution"},"text":"Player Two enters the game for Player One","participants":[{"athlete":{"id":"2"}},{"athlete":{"id":"1"}}]},
                {"sequenceNumber":"20","period":{"number":1},"clock":{"displayValue":"4:00"},"team":{"id":"9"},"type":{"text":"Substitution"},"text":"Player One enters the game for Player Two","participants":[{"athlete":{"id":"1"}},{"athlete":{"id":"2"}}]},
            ]}
        stints, anomalies = build_stints("g", summary, "9")
        self.assertFalse(anomalies)
        attempt = {"game_id":"g","player_id":"1","period":1,"clock":"2:00","sequence":30}
        row = attach_workload([attempt], stints)[0]
        self.assertEqual(row["continuous_stint_seconds"], 120)
        self.assertEqual(row["cumulative_seconds_played"], 360)
        self.assertEqual(row["previous_bench_rest_seconds"], 240)
        self.assertEqual(row["stint_number"], 2)

    def test_flags_impossible_substitution(self):
        summary = {"boxscore":{"players":[]},"plays":[{"sequenceNumber":"1","period":{"number":1},"clock":{"displayValue":"5:00"},"team":{"id":"9"},"type":{"text":"Substitution"},"participants":[{"athlete":{"id":"2"}},{"athlete":{"id":"1"}}]}]}
        _, anomalies = build_stints("g", summary, "9")
        self.assertTrue(anomalies)

    def test_uses_event_order_when_source_sequence_is_nonmonotonic(self):
        summary = {"boxscore":{"players":[{"team":{"id":"9"},"statistics":[{"athletes":[
            {"starter":True,"athlete":{"id":"1"}}, {"starter":False,"athlete":{"id":"2"}}
        ]}]}]},"plays":[
            {"sequenceNumber":"100","period":{"number":1},"clock":{"displayValue":"8:00"},"team":{"id":"9"},"type":{"text":"Substitution"},"participants":[{"athlete":{"id":"2"}},{"athlete":{"id":"1"}}]},
            {"sequenceNumber":"10","period":{"number":1},"clock":{"displayValue":"4:00"},"team":{"id":"9"},"type":{"text":"Substitution"},"participants":[{"athlete":{"id":"1"}},{"athlete":{"id":"2"}}]},
        ]}
        stints, _ = build_stints("g", summary, "9")
        row = attach_workload([{"game_id":"g","player_id":"1","period":1,"clock":"2:00","sequence":5,"event_index":2}], stints)[0]
        self.assertEqual(row["continuous_stint_seconds"], 120)


if __name__ == "__main__":
    unittest.main()
