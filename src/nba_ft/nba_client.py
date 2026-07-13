from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path


class DataSourceError(RuntimeError):
    pass


class NbaClient:
    def __init__(self, cache_dir: Path, opener=urllib.request.urlopen):
        self.cache_dir = Path(cache_dir)
        self.opener = opener

    def fetch_json(self, url: str, cache_path: Path) -> dict:
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        error = None
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 NBA-FT-Research/0.1",
                    "Referer": "https://www.nba.com/",
                    "Accept": "application/json",
                })
                with self.opener(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
                temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                temporary.replace(cache_path)
                return payload
            except Exception as exc:
                error = exc
                if attempt < 2:
                    time.sleep(0.25 * (attempt + 1))
        raise DataSourceError(f"Could not retrieve {url}: {error}")

    def get_play_by_play(self, game_id: str) -> dict:
        url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
        return self.fetch_json(url, self.cache_dir / "games" / game_id / "playbyplay.json")

    def get_box_score(self, game_id: str) -> dict:
        url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
        return self.fetch_json(url, self.cache_dir / "games" / game_id / "boxscore.json")

