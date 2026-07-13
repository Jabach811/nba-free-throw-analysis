from __future__ import annotations


def period_duration(period: int) -> int:
    return 720 if period <= 4 else 300


def clock_seconds_remaining(clock: str) -> float:
    if not clock:
        return 0.0
    if ":" not in clock:
        return float(clock)
    minutes, seconds = clock.split(":", 1)
    return int(minutes) * 60 + float(seconds)


def game_elapsed(period: int, clock: str) -> float:
    prior = sum(period_duration(p) for p in range(1, period))
    remaining = clock_seconds_remaining(clock) if clock else period_duration(period)
    return prior + period_duration(period) - remaining


def build_stints(game_id: str, summary: dict, team_id: str):
    active, names, stints, anomalies = {}, {}, [], []
    for block in summary.get("boxscore", {}).get("players", []):
        if str(block.get("team", {}).get("id")) != str(team_id):
            continue
        for group in block.get("statistics", []):
            for entry in group.get("athletes", []):
                athlete = entry.get("athlete", {})
                pid = str(athlete.get("id"))
                names[pid] = athlete.get("displayName", pid)
                if entry.get("starter"):
                    active[pid] = {"start": 0.0, "start_sequence": 0, "start_event_index": 0, "period": 1, "clock": "12:00"}

    max_period = 4
    for event_index, play in enumerate(summary.get("plays", [])):
        period = int(play.get("period", {}).get("number", 1))
        max_period = max(max_period, period)
        if str(play.get("team", {}).get("id")) != str(team_id) or "substitution" not in play.get("type", {}).get("text", "").lower():
            continue
        participants = [str(x.get("athlete", {}).get("id")) for x in play.get("participants", [])]
        if len(participants) < 2:
            anomalies.append({"game_id": game_id, "sequence": play.get("sequenceNumber"), "reason": "substitution missing participants"})
            continue
        entering, leaving = participants[0], participants[1]
        elapsed = game_elapsed(period, play.get("clock", {}).get("displayValue", ""))
        sequence = int(play.get("sequenceNumber", 0))
        if leaving not in active:
            anomalies.append({"game_id": game_id, "sequence": sequence, "player_id": leaving, "reason": "leaving player not active"})
        else:
            start = active.pop(leaving)
            stints.append({"game_id": game_id, "player_id": leaving, "player_name": names.get(leaving, leaving),
                "start_elapsed": start["start"], "end_elapsed": elapsed,
                "start_sequence": start["start_sequence"], "end_sequence": sequence,
                "start_event_index": start["start_event_index"], "end_event_index": event_index,
                "duration_seconds": max(0, elapsed - start["start"]), "confidence": "high"})
        if entering in active:
            anomalies.append({"game_id": game_id, "sequence": sequence, "player_id": entering, "reason": "entering player already active"})
        else:
            active[entering] = {"start": elapsed, "start_sequence": sequence, "start_event_index": event_index, "period": period, "clock": play.get("clock", {}).get("displayValue", "")}

    end_elapsed = sum(period_duration(p) for p in range(1, max_period + 1))
    end_sequence = 10**12
    for pid, start in active.items():
        stints.append({"game_id": game_id, "player_id": pid, "player_name": names.get(pid, pid),
            "start_elapsed": start["start"], "end_elapsed": end_elapsed,
            "start_sequence": start["start_sequence"], "end_sequence": end_sequence,
            "start_event_index": start["start_event_index"], "end_event_index": 10**12,
            "duration_seconds": max(0, end_elapsed - start["start"]), "confidence": "high"})

    counts = {}
    for stint in sorted(stints, key=lambda x: (x["player_id"], x["start_elapsed"], x["start_sequence"])):
        pid = stint["player_id"]
        counts[pid] = counts.get(pid, 0) + 1
        stint["stint_number"] = counts[pid]
    return stints, anomalies


def attach_workload(attempts: list[dict], stints: list[dict]) -> list[dict]:
    by_player = {}
    for stint in stints:
        by_player.setdefault((stint["game_id"], stint["player_id"]), []).append(stint)
    for values in by_player.values():
        values.sort(key=lambda x: (x["start_elapsed"], x["start_sequence"]))

    output = []
    for original in attempts:
        row = dict(original)
        elapsed = game_elapsed(int(row["period"]), row["clock"])
        candidates = by_player.get((row["game_id"], str(row["player_id"])), [])
        event_index = int(row.get("event_index", row["sequence"]))
        current = next((s for s in candidates if s["start_event_index"] <= event_index < s["end_event_index"]), None)
        if current is None:
            row.update({"continuous_stint_seconds":"", "cumulative_seconds_played":"", "previous_bench_rest_seconds":"", "stint_number":"", "workload_confidence":"low"})
        else:
            prior = [s for s in candidates if s["end_event_index"] <= current["start_event_index"]]
            previous = prior[-1] if prior else None
            row.update({
                "continuous_stint_seconds": round(max(0, elapsed - current["start_elapsed"]), 1),
                "cumulative_seconds_played": round(sum(s["duration_seconds"] for s in prior) + max(0, elapsed - current["start_elapsed"]), 1),
                "previous_bench_rest_seconds": round(current["start_elapsed"] - previous["end_elapsed"], 1) if previous else "",
                "stint_number": current["stint_number"], "workload_confidence": current["confidence"],
            })
        output.append(row)
    return output
