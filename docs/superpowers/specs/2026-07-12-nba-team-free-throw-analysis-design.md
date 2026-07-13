# NBA Team Free-Throw Analysis Design

## Objective

Extend the reusable NBA free-throw analyzer from a player-season tool into a scalable team-season pipeline. The Golden State Warriors 2025-26 season is the prototype. Include regular season, Play-In, and playoffs; exclude preseason, exhibitions, and All-Star games.

## Population

Include every player credited with at least one official free-throw attempt for Golden State in an eligible game. Include players who were traded, waived, or on short contracts. Determine membership from actual free-throw events, not the final roster.

## Architecture

Use a team-first single-pass pipeline. Download and cache each eligible Warriors game once, normalize the full event stream, reconstruct player stints and free-throw trips, and derive player outputs from one team ledger. Player totals must aggregate exactly to team totals.

Keep four layers separate:

1. Immutable source responses organized by game ID.
2. Normalized event and stint records.
3. Attempt- and trip-level classified records.
4. Reports and dashboard-ready aggregates.

All team-specific values are runtime inputs. No Warriors player, roster, or game exception may be hard-coded.

## Attempt Ledger

Each free-throw attempt records:

- Player name and stable source player ID
- Team, opponent, game ID, date, season segment, and game number
- Home or away status
- Period, regulation quarter or overtime number, game clock, and wall-clock timestamp
- Score before the attempt, score margin, leading/trailing/tied state, and clutch state
- Made or missed result
- Attempt position and announced trip length
- Stable reconstructed trip ID and complete prior-result history within the trip
- Trip type and initiating foul/play
- Timeout, review/challenge, substitution, and other intervening events
- Immediate or interrupted status
- Seconds since the preceding event and preceding free throw when timestamps permit
- Player attempts and trips already taken in the game
- Team attempts and trips already taken in the game
- Continuous on-court stint duration before the attempt
- Estimated cumulative game minutes played before the attempt
- Previous bench-rest duration and completed stint count
- Days since the prior team game, back-to-back status, and games in recent rolling windows
- Raw event description, source event IDs, confidence, and anomaly notes

Labels overlap. Position, trip type, workload, game context, and interruption labels may all apply to one attempt.

## Free-Throw Classification

Preserve the validated player analyzer's supported types: ordinary shooting, and-one, technical, defensive three seconds, transition take, clear path, flagrant, away-from-play, and other.

Determine sequence position from structured event text first. Reuse the first attempt's trip classification for later attempts in the same trip. Treat an explicit technical-free-throw description without `1 of 1` as a high-confidence single attempt.

Count interruptions only between the initiating foul/play and the attempt. Do not use an arbitrary backward event window.

## Stint and Workload Reconstruction

Reconstruct continuous on-court stints from starters, substitutions, period boundaries, and overtime boundaries. For each attempt, calculate:

- Seconds in the current stint
- Estimated cumulative seconds played before the attempt
- Seconds of bench rest before the current stint
- Number of prior completed stints

These fields are workload proxies, not direct measurements of fatigue. A missing starter record, contradictory substitution, or impossible player count reduces confidence and appears in validation. Do not silently fabricate stint timing.

## Required Splits

Report makes, attempts, misses, and percentage for:

- Overall, regular season, Play-In, and playoffs
- Home and away
- Every regulation quarter and overtime
- Attempt positions within one-, two-, and three-shot trips
- `2 of 2` after making the first and after missing the first
- Three-shot conditional histories
- Every supported trip type
- Immediate and interrupted attempts
- Timeout, review/challenge, substitution, and other interruption classes
- Leading, tied, trailing, and clutch contexts
- Continuous-stint and cumulative-minutes workload bands
- Rest and schedule-context bands

Zero-attempt categories remain visible as `N/A`. Every percentage displays its attempt count.

## Findings Engine

Generate separate team and player key-findings artifacts. Findings prioritize interpretable contrasts such as attempt-position effects, home/away differences, quarter patterns, workload bands, clutch context, and immediate versus interrupted attempts.

Each finding includes the compared makes, attempts, percentages, percentage-point difference, and sample-size qualifier. Use descriptive language for small samples and stronger language only when the sample supports it. Findings are exploratory, not causal claims.

## Outputs

Produce:

- Team-wide attempt CSV
- Team-wide trip CSV
- Normalized stint CSV
- Player summary table
- One summary and key-findings file per qualifying player
- Team summary and team key-findings file
- Dashboard-ready versioned JSON bundle
- Validation report and machine-readable manifest
- Cached raw game responses

The JSON bundle contains schema version, team and season metadata, players, attempts, trips, stints, precomputed splits, findings, validation state, and source provenance.

## Validation

For every eligible game:

1. Team attempts reconcile with the official team box score.
2. Each player's attempts reconcile with the player box score.
3. Player attempts sum exactly to team attempts.
4. Attempt rows reproduce all summaries and findings.
5. Every low-confidence classification or stint appears in validation.

The run is incomplete if any game fails download or reconciliation. Successfully cached games remain reusable after a partial failure.

## Recursive Skill Improvement

After every completed player or team run:

1. Inspect source failures, reconciliation mismatches, low-confidence records, and missing useful dimensions.
2. Convert generalizable discoveries into regression fixtures and rules.
3. Update the analyzer and skill instructions only for generalizable behavior.
4. Validate the skill structure and run the complete automated suite.
5. Re-run cached Curry and Brunson regression datasets.
6. Document intentional corrections through schema version and validation evidence.

Never add undocumented player-specific exceptions. A refinement that changes a prior verified total must identify the affected source events and explain the correction.

## Dashboard Boundary

This phase produces complete data and dashboard-ready JSON but does not implement the HTML interface. Dashboard visual design begins only after the Warriors data passes validation. The later interface will support team overview, player navigation, player findings, comparison charts, and filtering from the same reusable dataset.

## Acceptance Criteria

The Warriors prototype is accepted when:

1. Every eligible Warriors game is discovered and cached once.
2. Every qualifying player is included.
3. Team and player attempts reconcile for every game and season segment.
4. Home/away, period, game context, and workload fields are populated or explicitly confidence-flagged.
5. Player and team findings reproduce from the attempt ledger.
6. Dashboard JSON validates against its schema version.
7. Curry and Brunson regression outputs remain verified or have documented source-level corrections.
