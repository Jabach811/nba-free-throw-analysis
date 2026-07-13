from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SEGMENTS = {"002": "Regular Season", "005": "Play-In", "004": "Playoffs"}


def segment_from_game_id(game_id: str) -> str:
    try:
        return SEGMENTS[game_id[:3]]
    except KeyError as exc:
        raise ValueError(f"Unsupported NBA game type: {game_id}") from exc


@dataclass(frozen=True)
class GameRef:
    game_id: str
    date: str
    opponent: str
    segment: str


@dataclass(frozen=True)
class RawEvent:
    game_id: str
    sequence: int
    period: int
    clock: str
    action_type: str
    sub_type: str
    description: str
    person_id: int | None
    team_id: int | None
    score_home: int | None = None
    score_away: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FreeThrowAttempt:
    game_id: str
    trip_id: str
    event_sequence: int
    player_id: int
    period: int
    clock: str
    made: bool
    attempt_number: int
    trip_length: int
    trip_type: str
    previous_result: str | None
    initiating_sequence: int | None
    interruptions: tuple[str, ...]
    confidence: str
    anomaly: str = ""
    description: str = ""


@dataclass(frozen=True)
class FreeThrowTrip:
    trip_id: str
    game_id: str
    player_id: int
    trip_type: str
    attempts: tuple[FreeThrowAttempt, ...]
    initiating_sequence: int | None
    interruptions: tuple[str, ...]
    confidence: str
    anomaly: str = ""


@dataclass(frozen=True)
class ValidationResult:
    game_id: str
    expected_fta: int | None
    actual_fta: int
    passed: bool
    message: str
