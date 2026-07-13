from __future__ import annotations

import csv
import json
import re
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path


FT_RE = re.compile(r"(\d+)\s+of\s+(\d+)", re.I)
CURRY_ESPN_ID = "3975"


def _timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _participants(play):
    return {str(x.get("athlete", {}).get("id")) for x in play.get("participants", [])}


def _free_throw_type(prior, length):
    text = " | ".join(x.get("text", "").lower() for x in prior)
    for label, needles in (
        ("technical", ("technical foul",)), ("defensive-three-seconds", ("defensive 3", "defensive three")),
        ("transition-take", ("take foul",)), ("clear-path", ("clear path",)),
        ("flagrant", ("flagrant",)), ("away-from-play", ("away from play",))):
        if any(n in text for n in needles):
            return label
    made_shot = any((" makes " in f" {x.get('text','').lower()} " or "made" in x.get("type",{}).get("text","").lower())
                    and "free throw" not in x.get("text", "").lower() for x in prior)
    return "and-one" if length == 1 and made_shot else "shooting"


def classify_game(game_id, segment, payload, game_meta=None):
    plays = payload.get("plays", [])
    rows = []
    current_trip = None
    current_type = None
    current_interruptions = []
    previous_result = None
    previous_ft_time = None
    for i, play in enumerate(plays):
        text = play.get("text", "")
        type_text = play.get("type", {}).get("text", "")
        if "free throw" not in (type_text + " " + text).lower() or CURRY_ESPN_ID not in _participants(play):
            continue
        match = FT_RE.search(type_text + " " + text)
        number, length = map(int, match.groups()) if match else (1, 1)
        prior = plays[max(0, i - 12):i]
        if number == 1 or current_trip is None:
            current_trip = f"{game_id}-{play.get('id', play.get('sequenceNumber'))}"
            previous_result = None
            previous_ft_time = None
            current_type = _free_throw_type(prior, length)
            foul_indexes = [n for n, p in enumerate(prior) if "foul" in (p.get("type", {}).get("text", "") + " " + p.get("text", "")).lower()]
            interruption_window = prior[(foul_indexes[-1] + 1 if foul_indexes else 0):]
            current_interruptions = []
        interruptions = current_interruptions
        for p in (interruption_window if number == 1 else []):
            low = (p.get("type", {}).get("text", "") + " " + p.get("text", "")).lower()
            if "timeout" in low: interruptions.append("timeout")
            if "review" in low or "challenge" in low: interruptions.append("review/challenge")
            if "substitution" in low or "enters the game" in low: interruptions.append("substitution")
        interruptions = list(dict.fromkeys(interruptions))
        wallclock = _timestamp(play.get("wallclock"))
        made = "miss" not in text.lower()
        inferred_technical = not match and "technical free throw" in text.lower()
        meta = game_meta or {}
        rows.append({
            "game_id": game_id, "date": meta.get("date", ""), "opponent": meta.get("opponent", ""),
            "segment": segment, "trip_id": current_trip, "event_id": play.get("id", ""),
            "sequence": int(play.get("sequenceNumber", len(rows))), "period": play.get("period", {}).get("number"),
            "clock": play.get("clock", {}).get("displayValue", ""), "wallclock": play.get("wallclock", ""),
            "made": made, "attempt_number": number, "trip_length": length,
            "position": f"{number} of {length}", "previous_result": previous_result or "",
            "trip_type": current_type, "timeout_before": "timeout" in interruptions,
            "review_before": "review/challenge" in interruptions, "substitution_before": "substitution" in interruptions,
            "interrupted": bool(interruptions), "interruptions": ";".join(interruptions),
            "seconds_since_previous_ft": int((wallclock - previous_ft_time).total_seconds()) if wallclock and previous_ft_time else "",
            "seconds_since_prior_play": int((wallclock - _timestamp(plays[i-1].get("wallclock"))).total_seconds()) if i and wallclock and plays[i-1].get("wallclock") else "",
            "away_score": play.get("awayScore", ""), "home_score": play.get("homeScore", ""),
            "description": text, "confidence": "high" if match or inferred_technical else "medium", "anomaly": "" if match or inferred_technical else "missing sequence label",
        })
        previous_result = "made" if made else "missed"
        previous_ft_time = wallclock
    return rows


def fetch_json(url, path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NBA-FT-Research/0.1"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = json.load(response)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def _pct(makes, attempts):
    return "N/A" if not attempts else f"{100 * makes / attempts:.1f}%"


def eligible_games(log):
    result = {}
    for season_type in log.get("seasonTypes", []):
        name = season_type.get("displayName", "").lower()
        if "preseason" in name:
            continue
        segment = "Play-In" if "play in" in name else "Playoffs" if "playoff" in name or "postseason" in name else "Regular Season" if "regular season" in name else None
        if not segment:
            continue
        for category in season_type.get("categories", []):
            for event in category.get("events", []):
                ft = event.get("stats", ["", "", "", "", "", "0-0"])[5]
                expected = int(ft.split("-")[-1]) if "-" in ft else 0
                result[event["eventId"]] = {"segment": segment, "expected_fta": expected}
    return result


def write_outputs(rows, output, validations=None):
    output.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with (output / "curry_free_throws.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(rows)
    groups = defaultdict(list)
    for required in ("and-one immediate", "and-one interrupted", "and-one post-timeout", "and-one post-review/challenge", "and-one post-substitution", "all post-timeout", "all post-review/challenge", "2 of 2 after made", "2 of 2 after missed"):
        groups[required] = []
    for row in rows:
        groups["All attempts"].append(row)
        groups[row["segment"]].append(row)
        groups[row["position"]].append(row)
        groups[row["trip_type"]].append(row)
        if row["attempt_number"] == 2 and row["trip_length"] == 2: groups[f"2 of 2 after {row['previous_result']}"] .append(row)
        if row["attempt_number"] == 2 and row["trip_length"] == 3: groups[f"2 of 3 after {row['previous_result']}"] .append(row)
        if row["trip_type"] == "and-one" and row["timeout_before"]: groups["and-one post-timeout"].append(row)
        if row["trip_type"] == "and-one" and row["review_before"]: groups["and-one post-review/challenge"].append(row)
        if row["trip_type"] == "and-one" and row["substitution_before"]: groups["and-one post-substitution"].append(row)
        if row["trip_type"] == "and-one" and row["interrupted"]: groups["and-one interrupted"].append(row)
        if row["trip_type"] == "and-one" and not row["interrupted"]: groups["and-one immediate"].append(row)
        if row["timeout_before"]: groups["all post-timeout"].append(row)
        if row["review_before"]: groups["all post-review/challenge"].append(row)
    lines = ["# Stephen Curry Advanced Free Throws — 2025-26", "", "Regular season, Play-In, and playoffs", "", "| Split | Makes | Attempts | Misses | FT% |", "|---|---:|---:|---:|---:|"]
    for name, items in groups.items():
        makes = sum(bool(x["made"]) for x in items)
        lines.append(f"| {name} | {makes} | {len(items)} | {len(items)-makes} | {_pct(makes,len(items))} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    anomalies = [r for r in rows if r["anomaly"]]
    validations = validations or []
    mismatches = [v for v in validations if not v["passed"]]
    validation_lines = ["# Validation", "", f"Attempts: {len(rows)}", "", f"Games reconciled: {len(validations)-len(mismatches)} of {len(validations)}", "", f"Classification anomalies: {len(anomalies)}"]
    for item in mismatches:
        validation_lines.append(f"- {item['game_id']}: play-by-play {item['actual']}, box score {item['expected']}")
    (output / "validation.md").write_text("\n".join(validation_lines) + "\n", encoding="utf-8")


def run(base: Path):
    cache, output = base / "data" / "raw" / "espn", base / "output" / "curry-2025-26"
    log = fetch_json("https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/3975/gamelog?season=2026", cache / "gamelog.json")
    rows, failures, validations = [], [], []
    eligible = eligible_games(log)
    for game_id in sorted(eligible, key=lambda x: log.get("events", {}).get(x, {}).get("gameDate", "")):
        game = log.get("events", {}).get(game_id, {})
        try:
            summary = fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}", cache / "games" / f"{game_id}.json")
            segment = eligible[game_id]["segment"]
            meta = {"date": game.get("gameDate", "")[:10], "opponent": game.get("opponent", {}).get("abbreviation", "")}
            game_rows = classify_game(game_id, segment, summary, meta)
            rows.extend(game_rows)
            validations.append({"game_id": game_id, "actual": len(game_rows), "expected": eligible[game_id]["expected_fta"], "passed": len(game_rows) == eligible[game_id]["expected_fta"]})
        except Exception as exc:
            failures.append({"game_id": game_id, "error": str(exc)})
    write_outputs(rows, output, validations)
    mismatches = [v for v in validations if not v["passed"]]
    manifest = {"games_discovered": len(eligible), "games_failed": failures, "games_reconciled": len(validations)-len(mismatches), "reconciliation_mismatches": mismatches, "attempts": len(rows), "complete": not failures and not mismatches, "source": "ESPN public play-by-play and box-score game log"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(run(Path.cwd()), indent=2))
