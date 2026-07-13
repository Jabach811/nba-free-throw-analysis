---
name: nba-free-throw-analysis
description: Use when a user wants NBA player or team free throws broken down by attempt position, prior result, trip type, home/away, quarter, score state, clutch context, timeout, review, substitution, stint workload, delay, or complete season auditing.
---

# NBA Free-Throw Analysis

## Overview

Produce auditable player- or team-level NBA free-throw datasets from public play-by-play. Reconcile every game against player and team box-score FTA before reporting percentages.

## Workflow

1. Choose player mode or team mode.
2. Identify the ESPN athlete ID or team ID plus team abbreviation.
3. Interpret a season by its ending year: `2026` means 2025-26.
4. Run the matching bundled script with a dedicated output directory.
5. Require `complete: true`, zero reconciliation mismatches, and zero classification anomalies.
6. Inspect small or unusual buckets directly in `free_throw_attempts.csv`.
7. Report makes, attempts, misses, percentage, and sample size together. Display zero-attempt categories as `N/A`.

Player mode:

```powershell
python scripts/analyze_player.py `
  --player-id 3934672 `
  --player-name "Jalen Brunson" `
  --season-end-year 2026 `
  --work-dir "C:\analysis" `
  --output "C:\analysis\output\jalen-brunson-2025-26"
```

Team mode downloads every eligible game once and derives all players from the shared ledger:

```powershell
python scripts/analyze_team.py `
  --team-id 9 `
  --team-slug gs `
  --team-name "Golden State Warriors" `
  --season-end-year 2026 `
  --work-dir "C:\analysis" `
  --output "C:\analysis\output\warriors-2025-26"
```

## Integrity Rules

- Select eligible games from season-type membership. Never trust a flat event list that includes preseason.
- Include regular season, Play-In, and playoffs. Exclude preseason, exhibitions, and All-Star games.
- Include every team player with an official attempt, regardless of final-roster status.
- Treat position, trip type, interruption, game context, and workload as overlapping labels.
- Count interruptions only between the initiating foul/play and the attempt.
- Parse clocks without a colon as decimal seconds remaining in the minute.
- Use play-array position for chronological joins. Preserve ESPN `sequenceNumber` only as source evidence because it may be nonmonotonic.
- Treat continuous stint and cumulative minutes as workload proxies, not proof of fatigue.
- Cache source JSON separately from derived outputs.
- Surface mismatches, missing workload joins, and ambiguous records. Never force reconciliation silently.

## Outputs

Player mode creates attempt CSV, summary, validation, and manifest files. Team mode additionally creates trip and stint CSVs, player summaries and key findings, team findings, and schema-versioned `dashboard.json`.

Read [references/classification.md](references/classification.md) when changing classification, stint, or validation rules.

## Recursive Improvement

After each completed run, inspect mismatches, anomalies, missing dimensions, and misleading findings. Convert generalizable source behavior into regression tests before changing rules. Re-run prior cached integrity checks. Never add undocumented player-specific exceptions. Increment the dashboard schema version when output meaning or structure changes.

## Common Mistakes

- Flat-list discovery leaks preseason games.
- Broad backward scans falsely attach unrelated timeouts or technicals.
- Source sequence numbers can misjoin chronologically ordered events.
- Reporting percentages without attempts hides tiny samples.
- Calling zero observed events missing data confuses `0 attempts` with `not measured`.
- Treating every `1 of 1` as an and-one misclassifies technical and special attempts.
