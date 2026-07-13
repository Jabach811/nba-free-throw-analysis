from __future__ import annotations

import re

from .models import FreeThrowAttempt, FreeThrowTrip, RawEvent


SEQUENCE_RE = re.compile(r"(\d+)\s+of\s+(\d+)", re.I)
ADMIN_TYPES = {"timeout", "replay", "instant replay", "challenge", "substitution"}


def _kind(event: RawEvent) -> str:
    return event.action_type.lower().strip()


def _trip_type(events: list[RawEvent], start: int, length: int) -> tuple[str, int | None, tuple[str, ...]]:
    prior = events[max(0, start - 12):start]
    interruptions = tuple(dict.fromkeys(
        "review/challenge" if any(x in _kind(e) or x in e.sub_type.lower() for x in ("replay", "review", "challenge"))
        else "substitution" if "substitution" in _kind(e)
        else "timeout" if "timeout" in _kind(e)
        else _kind(e)
        for e in prior if _kind(e) in ADMIN_TYPES or any(x in _kind(e) for x in ("replay", "challenge"))
    ))
    foul = next((e for e in reversed(prior) if "foul" in _kind(e)), None)
    subtype = (foul.sub_type + " " + foul.description).lower() if foul else ""
    special = next((name for name, needles in {
        "technical": ("technical",), "defensive-three-seconds": ("defensive 3", "defensive three"),
        "transition-take": ("transition take", "take foul"), "clear-path": ("clear path",),
        "flagrant": ("flagrant",), "away-from-play": ("away from play",),
    }.items() if any(n in subtype for n in needles)), None)
    if special:
        return special, foul.sequence if foul else None, interruptions
    made_shot = next((e for e in reversed(prior) if _kind(e) in {"2pt", "3pt", "field goal"} and "miss" not in e.description.lower()), None)
    if length == 1 and made_shot and (not foul or made_shot.sequence < foul.sequence):
        return "and-one", foul.sequence if foul else made_shot.sequence, interruptions
    return "shooting" if foul else "other", foul.sequence if foul else None, interruptions


def classify_player_free_throws(events: list[RawEvent], player_id: int):
    attempts: list[FreeThrowAttempt] = []
    trip_groups: dict[str, list[FreeThrowAttempt]] = {}
    current_trip = None
    previous = None
    for index, event in enumerate(events):
        if event.person_id != player_id or "free throw" not in _kind(event):
            continue
        match = SEQUENCE_RE.search(event.sub_type or event.description)
        if match:
            number, length = map(int, match.groups())
        else:
            number = length = 1
        if number == 1 or current_trip is None:
            current_trip = f"{event.game_id}-{event.sequence}"
            previous = None
            trip_type, initiating, interruptions = _trip_type(events, index, length)
        made = str(event.raw.get("shotResult", "")).lower() == "made" or "miss" not in event.description.lower()
        attempt = FreeThrowAttempt(event.game_id, current_trip, event.sequence, player_id, event.period,
            event.clock, made, number, length, trip_type, previous, initiating, interruptions,
            "high" if match else "medium", "" if match else "Missing sequence label", event.description)
        attempts.append(attempt)
        trip_groups.setdefault(current_trip, []).append(attempt)
        previous = "made" if made else "missed"
    trips = [FreeThrowTrip(key, rows[0].game_id, player_id, rows[0].trip_type, tuple(rows),
             rows[0].initiating_sequence, rows[0].interruptions,
             "low" if any(r.confidence == "low" for r in rows) else rows[0].confidence,
             "; ".join(filter(None, (r.anomaly for r in rows)))) for key, rows in trip_groups.items()]
    return trips, attempts
