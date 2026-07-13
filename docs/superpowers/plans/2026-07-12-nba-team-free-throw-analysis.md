# NBA Team Free-Throw Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a reusable team-first free-throw pipeline for every Golden State player with an official 2025-26 attempt.

**Architecture:** Discover the eligible team schedule once, cache each game once, normalize team free throws and substitution context into a shared ledger, and derive player/team reports plus versioned dashboard JSON. Reconcile player and team totals against every game box score before marking the run complete.

**Tech Stack:** Python 3.11 standard library, ESPN public JSON feeds, `unittest`, CSV/JSON/Markdown.

## Global Constraints

- Include regular season, Play-In, and playoffs; exclude preseason, exhibitions, and All-Star games.
- Include every player with at least one official team free-throw attempt, including traded, waived, and short-contract players.
- Cache each game once and preserve immutable raw data separately from derived outputs.
- Treat stint metrics as workload proxies, not direct fatigue measurements.
- Never add player-specific exceptions; convert generalizable discoveries into regression tests.
- Preserve verified Curry and Brunson results unless a source-level correction is documented.

---

### Task 1: Team schedule and roster-free discovery

**Files:**
- Create: `src/nba_ft/team_pipeline.py`
- Test: `tests/test_team_pipeline.py`

**Interfaces:**
- Produces `discover_team_games(schedule: dict) -> dict[str, dict]` and `game_context(summary: dict, team_id: str) -> dict`.

- [ ] Write failing tests proving preseason exclusion, regular/Play-In/playoff mapping, home/away detection, opponent detection, and inclusion of zero-FTA games for validation.
- [ ] Run `python -m unittest tests.test_team_pipeline -v`; expect missing imports.
- [ ] Implement discovery from schedule season-type membership and game context from header competitors.
- [ ] Re-run the tests; expect passes.

### Task 2: Team attempt classification and score context

**Files:**
- Modify: `src/nba_ft/team_pipeline.py`
- Test: `tests/test_team_pipeline.py`

**Interfaces:**
- Produces `classify_team_game(game_id, segment, summary, team_id, metadata) -> list[dict]`.

- [ ] Add failing fixtures for multiple shooters, first/second conditional results, special trip types, bounded interruptions, home/away, quarter/overtime, score margin, and clutch state.
- [ ] Run the focused tests; expect failures for missing fields.
- [ ] Implement multi-player trip state keyed by shooter, team filtering, pre-attempt score reconstruction, and overlapping context fields.
- [ ] Re-run focused tests; expect passes.

### Task 3: Stint and workload reconstruction

**Files:**
- Create: `src/nba_ft/stints.py`
- Test: `tests/test_stints.py`

**Interfaces:**
- Produces `build_stints(summary: dict, team_id: str) -> tuple[list[dict], list[dict]]` and `attach_workload(attempts, stints) -> list[dict]`.

- [ ] Write failing tests for starters, substitutions, period boundaries, continuous stint seconds, cumulative seconds, previous bench rest, stint count, and contradictory substitutions.
- [ ] Run `python -m unittest tests.test_stints -v`; expect missing imports.
- [ ] Implement event-clock conversion and confidence-flagged stint reconstruction. Leave values blank when evidence is insufficient.
- [ ] Re-run tests; expect passes.

### Task 4: Team/player summaries and findings

**Files:**
- Create: `src/nba_ft/team_report.py`
- Test: `tests/test_team_report.py`

**Interfaces:**
- Produces `aggregate(rows, filters)`, `generate_findings(rows, scope_name)`, and `write_team_outputs(...)`.

- [ ] Write failing tests for home/away, periods, score state, workload bands, conditional second attempts, small-sample wording, team/player totals, and zero-attempt categories.
- [ ] Run `python -m unittest tests.test_team_report -v`; expect missing imports.
- [ ] Implement deterministic summaries, evidence-bearing findings, attempt/trip/stint CSVs, per-player artifacts, and schema-versioned dashboard JSON.
- [ ] Re-run tests; expect passes.

### Task 5: End-to-end validation and CLI

**Files:**
- Modify: `src/nba_ft/team_pipeline.py`
- Create: `src/nba_ft/team_cli.py`
- Test: `tests/test_team_end_to_end.py`

**Interfaces:**
- CLI: `python -m nba_ft.team_cli --team-id 9 --team-name "Golden State Warriors" --season-end-year 2026 --output output/warriors-2025-26`.

- [ ] Write a failing fake-season test proving per-game player reconciliation, team reconciliation, resumable caching, manifest completeness, and failure recording.
- [ ] Run the focused test; expect failure.
- [ ] Implement the orchestrator and CLI with a nonzero exit code for incomplete runs.
- [ ] Run the full test suite; expect zero failures.

### Task 6: Warriors run and recursive skill refinement

**Files:**
- Modify: `skill-development/nba-free-throw-analysis/SKILL.md`
- Create: `skill-development/nba-free-throw-analysis/scripts/analyze_team.py`
- Modify: `skill-development/nba-free-throw-analysis/references/classification.md`

**Interfaces:**
- Installed skill gains reusable player and team modes with schema version `2.0`.

- [ ] Run the complete Warriors season and inspect every mismatch or low-confidence stint.
- [ ] Add regression fixtures for generalizable source behavior uncovered by the run.
- [ ] Re-run the complete automated suite and cached Curry/Brunson integrity checks.
- [ ] Validate the staged skill, deploy it to the personal skill directory, and validate the installed copy.
- [ ] Verify team/player/game reconciliation, dashboard JSON schema version, key findings, and all output artifacts.

## Final Verification

- [ ] Run `python -m unittest discover -s tests -v`; require zero failures.
- [ ] Require Warriors manifest `complete: true` and zero reconciliation mismatches.
- [ ] Require player attempts to sum exactly to team attempts.
- [ ] Require zero unexplained classification anomalies and surface every low-confidence stint.
- [ ] Regenerate from cache and confirm deterministic attempt totals and findings.
