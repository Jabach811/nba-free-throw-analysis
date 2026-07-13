import unittest

from nba_ft.classify import classify_player_free_throws
from nba_ft.models import RawEvent


def event(seq, kind, subtype, desc, person=201939):
    return RawEvent("0022500001", seq, 4, "PT01M00.00S", kind, subtype, desc, person, 1610612744,
                    raw={"shotResult": "Missed" if desc.startswith("MISS") else "Made"})


class ClassifierTests(unittest.TestCase):
    def test_second_attempt_conditions_on_first(self):
        events = [
            event(10, "foul", "shooting", "Shooting foul", 9),
            event(11, "free throw", "1 of 2", "Curry Free Throw 1 of 2"),
            event(12, "free throw", "2 of 2", "MISS Curry Free Throw 2 of 2"),
        ]
        trips, attempts = classify_player_free_throws(events, 201939)
        self.assertEqual(len(trips), 1)
        self.assertEqual(attempts[1].previous_result, "made")
        self.assertEqual(attempts[1].trip_type, "shooting")

    def test_delayed_and_one_retains_timeout_label(self):
        events = [
            event(20, "2pt", "layup", "Curry makes layup"),
            event(21, "foul", "shooting", "Shooting foul", 9),
            event(22, "timeout", "full", "Warriors timeout", None),
            event(23, "free throw", "1 of 1", "Curry Free Throw 1 of 1"),
        ]
        _, attempts = classify_player_free_throws(events, 201939)
        self.assertEqual(attempts[0].trip_type, "and-one")
        self.assertIn("timeout", attempts[0].interruptions)


if __name__ == "__main__":
    unittest.main()
