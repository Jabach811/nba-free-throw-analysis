import unittest

from nba_ft.espn_pipeline import classify_game, eligible_games


class EspnPipelineTests(unittest.TestCase):
    def test_classifies_conditional_and_wallclock_delay(self):
        payload = {"plays": [
            {"id":"1","sequenceNumber":"1","type":{"text":"Shooting Foul"},"text":"Shooting foul","period":{"number":4},"clock":{"displayValue":"1:00"},"wallclock":"2026-01-01T00:00:00Z"},
            {"id":"2","sequenceNumber":"2","type":{"text":"Free Throw - 1 of 2"},"text":"Stephen Curry misses free throw 1 of 2","period":{"number":4},"clock":{"displayValue":"1:00"},"wallclock":"2026-01-01T00:00:10Z","participants":[{"athlete":{"id":"3975"}}]},
            {"id":"3","sequenceNumber":"3","type":{"text":"Free Throw - 2 of 2"},"text":"Stephen Curry makes free throw 2 of 2","period":{"number":4},"clock":{"displayValue":"1:00"},"wallclock":"2026-01-01T00:00:30Z","participants":[{"athlete":{"id":"3975"}}]},
        ]}
        rows = classify_game("g1", "Regular Season", payload)
        self.assertEqual(rows[1]["previous_result"], "missed")
        self.assertEqual(rows[1]["seconds_since_previous_ft"], 20)

    def test_old_timeout_does_not_label_unrelated_trip(self):
        payload = {"plays": [
            {"id":"1","sequenceNumber":"1","type":{"text":"Timeout"},"text":"Timeout","period":{"number":1},"clock":{"displayValue":"5:00"}},
            {"id":"2","sequenceNumber":"2","type":{"text":"Shooting Foul"},"text":"Shooting foul","period":{"number":1},"clock":{"displayValue":"4:00"}},
            {"id":"3","sequenceNumber":"3","type":{"text":"Free Throw - 1 of 2"},"text":"Stephen Curry makes free throw 1 of 2","period":{"number":1},"clock":{"displayValue":"4:00"},"participants":[{"athlete":{"id":"3975"}}]},
        ]}
        self.assertFalse(classify_game("g1", "Regular Season", payload)[0]["timeout_before"])

    def test_eligible_games_excludes_preseason(self):
        log = {"seasonTypes": [
            {"displayName":"2025-26 Regular Season","categories":[{"events":[{"eventId":"r","stats":["0","0","0","0","0","2-3"]}]}]},
            {"displayName":"2025-26 Preseason","categories":[{"events":[{"eventId":"p","stats":["0","0","0","0","0","4-4"]}]}]},
        ]}
        self.assertEqual(eligible_games(log), {"r": {"segment":"Regular Season", "expected_fta":3}})


if __name__ == "__main__":
    unittest.main()
