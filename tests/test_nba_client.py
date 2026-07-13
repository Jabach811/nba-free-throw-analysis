import json
import tempfile
import unittest
from pathlib import Path

from nba_ft.nba_client import NbaClient


class ClientTests(unittest.TestCase):
    def test_cache_prevents_second_fetch(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            return type("Response", (), {"read": lambda self: b'{"ok": true}', "__enter__": lambda self: self, "__exit__": lambda *a: None})()
        with tempfile.TemporaryDirectory() as tmp:
            client = NbaClient(Path(tmp), opener=opener)
            path = Path(tmp) / "x.json"
            self.assertTrue(client.fetch_json("https://example.test/x", path)["ok"])
            self.assertTrue(client.fetch_json("https://example.test/x", path)["ok"])
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
