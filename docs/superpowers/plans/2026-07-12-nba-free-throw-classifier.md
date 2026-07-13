# NBA Free-Throw Classifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run an auditable classifier for every Stephen Curry free throw in the 2025-26 regular season, Play-In, and playoffs.

**Architecture:** A Python package discovers eligible games, caches official NBA JSON, normalizes events, reconstructs free-throw trips, applies multi-label classifications, validates counts, and writes CSV/Markdown reports. Raw source data stays immutable; all derived outputs can be regenerated locally.

**Tech Stack:** Python 3.11+, standard library HTTP/JSON/CSV, `unittest` for tests.

## Global Constraints

- Curry's NBA player ID is `201939`; Golden State's team ID is `1610612744`.
- Include 2025-26 regular season, Play-In, and playoffs; exclude preseason, exhibition, and All-Star games.
- Never silently guess: inferred and anomalous records carry confidence and notes.
- Reconcile attempt counts against official box scores at game and segment level.
- Cache raw JSON by endpoint and game ID; never mix raw and derived records.
- Treat timeout, review/challenge, substitution, and other interruptions as separate multi-label attributes.

---

### Task 1: Package skeleton and domain models

**Files:**
- Create: `pyproject.toml`
- Create: `src/nba_ft/__init__.py`
- Create: `src/nba_ft/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `GameRef`, `RawEvent`, `FreeThrowAttempt`, and `FreeThrowTrip` dataclasses; `segment_from_game_id(game_id: str) -> str`.

- [ ] Write tests asserting valid regular-season (`002`), Play-In (`005`), and playoff (`004`) segment mapping and rejection of unsupported IDs.
- [ ] Run `python -m unittest tests.test_models -v`; expect failures because the package does not exist.
- [ ] Add package metadata and frozen dataclasses with explicit fields for source IDs, context, labels, confidence, and anomaly notes.
- [ ] Re-run the model tests; expect all to pass.

### Task 2: Official NBA acquisition and immutable cache

**Files:**
- Create: `src/nba_ft/nba_client.py`
- Test: `tests/test_nba_client.py`

**Interfaces:**
- Consumes: `GameRef`.
- Produces: `NbaClient.fetch_json(url: str, cache_path: Path) -> dict`, `get_schedule(season: str) -> dict`, `get_play_by_play(game_id: str) -> dict`, and `get_box_score(game_id: str) -> dict`.

- [ ] Write tests with a fake opener proving cache hits perform no network call, cache misses write exact JSON, invalid JSON raises `DataSourceError`, and retries stop after three failures.
- [ ] Run the client tests; expect import failures.
- [ ] Implement atomic cache writes through a temporary sibling file, a descriptive user agent, bounded timeout, three retries, and endpoint fallbacks between official NBA CDN/live-data resources where available.
- [ ] Re-run the client tests; expect all to pass.

### Task 3: Game discovery and event normalization

**Files:**
- Create: `src/nba_ft/discovery.py`
- Create: `src/nba_ft/normalize.py`
- Test: `tests/test_discovery.py`
- Test: `tests/test_normalize.py`
- Create: `tests/fixtures/sample_pbp.json`

**Interfaces:**
- Produces: `discover_games(schedule: dict, team_id: int, season: str) -> list[GameRef]` and `normalize_actions(payload: dict) -> list[RawEvent]`.

- [ ] Add fixtures and tests proving exclusions, segment classification, chronological event order, player IDs, action/subtype preservation, score context, raw descriptions, and correction metadata.
- [ ] Run both test modules; expect failures.
- [ ] Implement schema-tolerant traversal for the official schedule and live play-by-play action formats. Preserve original event sequence numbers and full raw action dictionaries.
- [ ] Re-run both test modules; expect all to pass.

### Task 4: Trip reconstruction and classification

**Files:**
- Create: `src/nba_ft/classify.py`
- Test: `tests/test_classify.py`
- Create: `tests/fixtures/free_throw_scenarios.json`

**Interfaces:**
- Consumes: ordered `list[RawEvent]`, shooter player ID.
- Produces: `classify_player_free_throws(events: list[RawEvent], player_id: int) -> tuple[list[FreeThrowTrip], list[FreeThrowAttempt]]`.

- [ ] Encode fixtures for two-shot trips, `2 of 2` conditional results, three-shot trips, immediate and-one, timeout-delayed and-one, replay/challenge delay, technical, defensive-three-second, transition-take, flagrant, clear-path, away-from-play, rescinded events, and malformed sequences.
- [ ] Write assertions for trip membership, position, prior-result labels, initiating event, interruption labels, type labels, confidence, and anomalies.
- [ ] Run `python -m unittest tests.test_classify -v`; expect failures.
- [ ] Implement parsing of structured action types first and description regexes second. Group by shooter, period, clock, stated attempt index/count, and nearby sequence; scan backward across administrative events to identify the initiating foul or made basket.
- [ ] Re-run classification tests; expect all to pass.

### Task 5: Validation and reports

**Files:**
- Create: `src/nba_ft/validate.py`
- Create: `src/nba_ft/report.py`
- Test: `tests/test_validate.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Produces: `validate_game(attempts, box_score, player_id) -> ValidationResult`; `write_attempt_csv`, `write_trip_csv`, `write_summary_markdown`, and `write_validation_markdown`.

- [ ] Test exact reconciliation, mismatch diagnostics, zero-attempt percentages, conditional second/third-shot splits, interruption splits, segment splits, and reproducibility of summary totals from attempt rows.
- [ ] Run validation/report tests; expect failures.
- [ ] Implement pure aggregation functions and deterministic output ordering. Display makes, attempts, misses, and percentage; use `N/A` for zero attempts.
- [ ] Re-run validation/report tests; expect all to pass.

### Task 6: Resumable Curry pipeline and real-data run

**Files:**
- Create: `src/nba_ft/pipeline.py`
- Create: `src/nba_ft/cli.py`
- Create: `README.md`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces CLI: `python -m nba_ft.cli --season 2025-26 --player-id 201939 --team-id 1610612744 --output output/curry-2025-26`.

- [ ] Test a two-game fake run proving partial cache reuse, deterministic output, segment inclusion, failure manifest behavior, and refusal to mark incomplete data as complete.
- [ ] Run `python -m unittest tests.test_pipeline -v`; expect failures.
- [ ] Implement the orchestrator, CLI arguments, progress logging, `manifest.json`, and README usage. Continue past individual game failures while recording them; return a nonzero exit code if reconciliation is incomplete.
- [ ] Run the complete test suite; expect all tests to pass.
- [ ] Run the real Curry command and inspect every validation anomaly.
- [ ] Correct generalizable parsing rules with regression fixtures, rerun tests, and rerun only affected cached games.
- [ ] Confirm every eligible game and segment reconciles, then deliver attempt/trip CSVs, summary, validation report, and manifest.

## Final Verification

- [ ] Run `python -m unittest discover -s tests -v`; require zero failures.
- [ ] Regenerate reports entirely from cached raw JSON and compare hashes with the first successful output.
- [ ] Confirm attempt CSV totals equal summary totals and official segment totals.
- [ ] Confirm all low-confidence rows appear in the validation report.
- [ ] Search code and reports for `TBD`, `TODO`, and placeholder values; require no hits.
