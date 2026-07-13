import tempfile
import unittest
from pathlib import Path

from nba_ft.team_report import build_splits, generate_findings, write_team_outputs


ROWS = [
    {"player_id":"1","player_name":"Player One","made":False,"position":"1 of 2","attempt_number":1,"trip_length":2,"previous_result":"","venue":"home","period_label":"Q1","trip_type":"shooting","interrupted":False,"timeout_before":False,"review_before":False,"substitution_before":False,"score_state":"trailing","clutch":False,"continuous_stint_seconds":200,"cumulative_seconds_played":500,"trip_id":"a"},
    {"player_id":"1","player_name":"Player One","made":True,"position":"2 of 2","attempt_number":2,"trip_length":2,"previous_result":"missed","venue":"home","period_label":"Q1","trip_type":"shooting","interrupted":False,"timeout_before":False,"review_before":False,"substitution_before":False,"score_state":"trailing","clutch":False,"continuous_stint_seconds":210,"cumulative_seconds_played":510,"trip_id":"a"},
    {"player_id":"1","player_name":"Player One","made":True,"position":"1 of 1","attempt_number":1,"trip_length":1,"previous_result":"","venue":"away","period_label":"Q4","trip_type":"and-one","interrupted":True,"timeout_before":True,"review_before":False,"substitution_before":False,"score_state":"leading","clutch":True,"continuous_stint_seconds":700,"cumulative_seconds_played":1900,"trip_id":"b"},
]


class TeamReportTests(unittest.TestCase):
    def test_builds_home_away_and_conditional_splits(self):
        splits = {x["split"]:x for x in build_splits(ROWS)}
        self.assertEqual(splits["home"]["attempts"], 2)
        self.assertEqual(splits["away"]["attempts"], 1)
        self.assertEqual(splits["2 of 2 after missed"]["pct"], 100.0)

    def test_findings_include_evidence_and_small_sample_warning(self):
        findings = generate_findings(ROWS, "Player One")
        self.assertTrue(any("1/1" in x["text"] for x in findings))
        self.assertTrue(all("sample" in x["qualifier"].lower() for x in findings))

    def test_writes_dashboard_bundle_and_player_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_team_outputs(ROWS, [], [], output, {"team_name":"Test Team","season":"2025-26"}, [])
            self.assertTrue((output / "dashboard.json").exists())
            self.assertTrue((output / "players" / "player-one" / "key-findings.md").exists())


if __name__ == "__main__":
    unittest.main()
