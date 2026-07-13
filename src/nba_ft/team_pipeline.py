from __future__ import annotations

import re
import json
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from .stints import attach_workload, build_stints, clock_seconds_remaining
from .team_report import write_team_outputs


FT_RE = re.compile(r"(\d+)\s+of\s+(\d+)", re.I)
SEGMENT_TYPES = {2: "Regular Season", 3: "Playoffs", 5: "Play-In"}


def discover_team_games(schedules: list[dict]) -> dict[str, dict]:
    result = {}
    for schedule in schedules:
        for event in schedule.get("events", []):
            season_type = event.get("seasonType", {})
            type_id = int(season_type.get("type", season_type.get("id", 0)))
            if type_id in SEGMENT_TYPES:
                result[event["id"]] = {
                    "segment": SEGMENT_TYPES[type_id],
                    "date": event.get("date", "")[:10],
                    "event": event,
                }
    return result


def game_context(summary: dict, team_id: str) -> dict:
    competitors = summary.get("header", {}).get("competitions", [{}])[0].get("competitors", [])
    team = next((x for x in competitors if str(x.get("id", x.get("team", {}).get("id"))) == str(team_id)), {})
    opponent = next((x for x in competitors if str(x.get("id", x.get("team", {}).get("id"))) != str(team_id)), {})
    return {
        "venue": team.get("homeAway", ""),
        "opponent": opponent.get("team", {}).get("abbreviation", opponent.get("abbreviation", "")),
    }


def player_map_and_boxscore(summary: dict, team_id: str):
    players, expected = {}, {}
    for block in summary.get("boxscore", {}).get("players", []):
        if str(block.get("team", {}).get("id")) != str(team_id):
            continue
        for stat_group in block.get("statistics", []):
            keys = stat_group.get("keys", [])
            ft_index = keys.index("freeThrowsMade-freeThrowsAttempted") if "freeThrowsMade-freeThrowsAttempted" in keys else None
            for entry in stat_group.get("athletes", []):
                athlete = entry.get("athlete", {})
                pid = str(athlete.get("id"))
                players[pid] = athlete.get("displayName", athlete.get("shortName", pid))
                if ft_index is not None and len(entry.get("stats", [])) > ft_index:
                    value = entry["stats"][ft_index]
                    expected[pid] = int(value.split("-")[-1]) if "-" in value else 0
    return players, expected


def _clock_seconds(clock: str) -> float:
    return clock_seconds_remaining(clock)


def _timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _trip_type(prior: list[dict], length: int, current_text: str) -> str:
    text = (" | ".join(x.get("text", "") for x in prior) + " | " + current_text).lower()
    for label, needles in (
        ("technical", ("technical free throw", "technical foul")),
        ("defensive-three-seconds", ("defensive 3", "defensive three")),
        ("transition-take", ("take foul",)), ("clear-path", ("clear path",)),
        ("flagrant", ("flagrant",)), ("away-from-play", ("away from play",))):
        if any(n in text for n in needles):
            return label
    made_shot = any(" makes " in f" {p.get('text','').lower()} " and "free throw" not in p.get("text", "").lower() for p in prior)
    return "and-one" if length == 1 and made_shot else "shooting"


def classify_team_game(game_id: str, segment: str, summary: dict, team_id: str,
                       players: dict[str, str], metadata: dict) -> list[dict]:
    plays, rows = summary.get("plays", []), []
    trip_state = {}
    player_counts, team_attempts = {}, 0
    for i, play in enumerate(plays):
        if str(play.get("team", {}).get("id")) != str(team_id):
            continue
        combined = play.get("type", {}).get("text", "") + " " + play.get("text", "")
        if "free throw" not in combined.lower():
            continue
        participant_ids = [str(x.get("athlete", {}).get("id")) for x in play.get("participants", [])]
        player_id = next((x for x in participant_ids if x in players), participant_ids[0] if participant_ids else "")
        if not player_id:
            continue
        match = FT_RE.search(combined)
        number, length = map(int, match.groups()) if match else (1, 1)
        prior = plays[max(0, i - 12):i]
        if number == 1 or player_id not in trip_state:
            foul_positions = [n for n, p in enumerate(prior) if "foul" in (p.get("type", {}).get("text", "") + " " + p.get("text", "")).lower()]
            window = prior[(foul_positions[-1] + 1 if foul_positions else 0):]
            labels = []
            for p in window:
                low = (p.get("type", {}).get("text", "") + " " + p.get("text", "")).lower()
                if "timeout" in low: labels.append("timeout")
                if "review" in low or "challenge" in low: labels.append("review/challenge")
                if "substitution" in low or "enters the game" in low: labels.append("substitution")
            trip_state[player_id] = {
                "trip_id": f"{game_id}-{play.get('id', play.get('sequenceNumber'))}",
                "trip_type": _trip_type(prior, length, play.get("text", "")),
                "interruptions": list(dict.fromkeys(labels)), "previous": "", "previous_time": None,
            }
        state = trip_state[player_id]
        made = "miss" not in play.get("text", "").lower()
        away_after, home_after = int(play.get("awayScore", 0)), int(play.get("homeScore", 0))
        venue = metadata.get("venue", "")
        away_before = away_after - (1 if made and venue == "away" else 0)
        home_before = home_after - (1 if made and venue == "home" else 0)
        margin = (home_before - away_before) if venue == "home" else (away_before - home_before)
        period = int(play.get("period", {}).get("number", 0))
        clock = play.get("clock", {}).get("displayValue", "")
        wallclock = _timestamp(play.get("wallclock"))
        player_counts[player_id] = player_counts.get(player_id, 0) + 1
        team_attempts += 1
        rows.append({
            "game_id": game_id, "date": metadata.get("date", ""), "segment": segment,
            "team_id": str(team_id), "opponent": metadata.get("opponent", ""), "venue": venue,
            "player_id": player_id, "player_name": players.get(player_id, player_id),
            "trip_id": state["trip_id"], "event_id": play.get("id", ""),
            "sequence": int(play.get("sequenceNumber", len(rows))), "event_index": i, "period": period,
            "period_label": f"Q{period}" if period <= 4 else f"OT{period-4}", "clock": clock,
            "wallclock": play.get("wallclock", ""), "made": made, "attempt_number": number,
            "trip_length": length, "position": f"{number} of {length}",
            "previous_result": state["previous"], "trip_type": state["trip_type"],
            "interruptions": ";".join(state["interruptions"]),
            "timeout_before": "timeout" in state["interruptions"],
            "review_before": "review/challenge" in state["interruptions"],
            "substitution_before": "substitution" in state["interruptions"],
            "interrupted": bool(state["interruptions"]),
            "away_score_before": away_before, "home_score_before": home_before,
            "score_margin_before": margin, "score_state": "tied" if margin == 0 else "leading" if margin > 0 else "trailing",
            "clutch": period >= 4 and _clock_seconds(clock) <= 300 and abs(margin) <= 5,
            "player_attempt_number_game": player_counts[player_id], "team_attempt_number_game": team_attempts,
            "seconds_since_previous_ft": int((wallclock - state["previous_time"]).total_seconds()) if wallclock and state["previous_time"] else "",
            "description": play.get("text", ""),
            "confidence": "high" if match or "technical free throw" in combined.lower() else "medium",
            "anomaly": "" if match or "technical free throw" in combined.lower() else "missing sequence label",
        })
        state["previous"] = "made" if made else "missed"
        state["previous_time"] = wallclock
    return rows


def validate_game(game_id: str, rows: list[dict], expected_by_player: dict[str, int]) -> dict:
    actual = Counter(str(x["player_id"]) for x in rows)
    player_ids = set(actual) | {str(k) for k, value in expected_by_player.items() if value}
    mismatches = [{"player_id":pid, "actual":actual.get(pid, 0), "expected":expected_by_player.get(pid, 0)}
                  for pid in sorted(player_ids) if actual.get(pid, 0) != expected_by_player.get(pid, 0)]
    return {"game_id":game_id, "team_actual":len(rows), "team_expected":sum(expected_by_player.values()),
            "player_mismatches":mismatches, "passed":not mismatches and len(rows) == sum(expected_by_player.values())}


def enrich_schedule_context(rows: list[dict]) -> list[dict]:
    game_dates = sorted({(x["date"], x["game_id"]) for x in rows})
    context, previous = {}, None
    for number, (value, game_id) in enumerate(game_dates, 1):
        current = date.fromisoformat(value)
        days_rest = "" if previous is None else max(0, (current - previous).days - 1)
        context[game_id] = {"team_game_number":number, "days_rest":days_rest,
                            "back_to_back": days_rest == 0 if previous is not None else False}
        previous = current
    return [dict(row, **context.get(row["game_id"], {})) for row in rows]


def fetch_json(url: str, path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    request = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 NBA-FT-Research/0.2"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = json.load(response)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
    return data


def _trips(attempts: list[dict]) -> list[dict]:
    grouped = {}
    for row in attempts: grouped.setdefault(row["trip_id"], []).append(row)
    result = []
    for trip_id, values in grouped.items():
        first = values[0]
        result.append({"trip_id":trip_id, "game_id":first["game_id"], "date":first["date"],
            "player_id":first["player_id"], "player_name":first["player_name"], "venue":first["venue"],
            "opponent":first["opponent"], "segment":first["segment"], "period":first["period"],
            "clock":first["clock"], "trip_type":first["trip_type"], "trip_length":first["trip_length"],
            "attempts":len(values), "makes":sum(bool(x["made"]) for x in values),
            "result_sequence":"-".join("M" if x["made"] else "X" for x in values),
            "interruptions":first["interruptions"]})
    return result


def run_team(base: Path, team_id: str, team_slug: str, team_name: str,
             season_end_year: int, output: Path) -> dict:
    season = f"{season_end_year-1}-{str(season_end_year)[-2:]}"
    cache = base / "data" / "raw" / "espn" / "teams" / str(team_id) / str(season_end_year)
    schedules, failures = [], []
    for season_type in (2, 3, 5):
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_slug}/schedule?season={season_end_year}&seasontype={season_type}"
        schedules.append(fetch_json(url, cache / f"schedule-{season_type}.json"))
    games = discover_team_games(schedules)
    attempts, stints, stint_anomalies, validations = [], [], [], []
    for game_id, info in sorted(games.items(), key=lambda x: x[1]["date"]):
        try:
            summary = fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}", cache / "games" / f"{game_id}.json")
            players, expected = player_map_and_boxscore(summary, team_id)
            context = dict(game_context(summary, team_id), date=info["date"])
            game_attempts = classify_team_game(game_id, info["segment"], summary, team_id, players, context)
            game_stints, anomalies = build_stints(game_id, summary, team_id)
            attempts.extend(attach_workload(game_attempts, game_stints)); stints.extend(game_stints)
            stint_anomalies.extend(anomalies); validations.append(validate_game(game_id, game_attempts, expected))
        except Exception as exc:
            failures.append({"game_id":game_id, "error":str(exc)})
    attempts = enrich_schedule_context(attempts)
    trips = _trips(attempts)
    metadata = {"team_id":str(team_id), "team_slug":team_slug, "team_name":team_name,
                "season":season, "season_end_year":season_end_year, "source":"ESPN public play-by-play and box score"}
    write_team_outputs(attempts, trips, stints, output, metadata, validations)
    mismatches = [x for x in validations if not x["passed"]]
    classification_anomalies = [x for x in attempts if x.get("anomaly")]
    manifest = {**metadata, "schema_version":"2.0", "games_discovered":len(games),
        "games_reconciled":len(validations)-len(mismatches), "games_failed":failures,
        "reconciliation_mismatches":mismatches, "players_with_attempts":len({x['player_id'] for x in attempts}),
        "attempts":len(attempts), "makes":sum(bool(x["made"]) for x in attempts),
        "classification_anomalies":len(classification_anomalies), "stint_anomalies":len(stint_anomalies),
        "complete":not failures and not mismatches and not classification_anomalies}
    output.mkdir(parents=True, exist_ok=True)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "stint-anomalies.json").write_text(json.dumps(stint_anomalies, indent=2), encoding="utf-8")
    lines = ["# Validation", "", f"Games reconciled: {manifest['games_reconciled']} of {manifest['games_discovered']}",
             f"Players with attempts: {manifest['players_with_attempts']}", f"Attempts: {manifest['attempts']}",
             f"Classification anomalies: {manifest['classification_anomalies']}", f"Stint anomalies: {manifest['stint_anomalies']}"]
    (output / "validation.md").write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    return manifest
