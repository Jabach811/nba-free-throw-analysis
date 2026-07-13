# NBA Free-Throw Intelligence

Play-by-play NBA free-throw analysis that classifies every official attempt by sequence, prior-result dependency, game context, interruption state, location, quarter, clutch state, and workload proxies.

The current prototype covers the Golden State Warriors' complete 2025-26 regular season and Play-In schedule:

- 85 of 85 games reconciled
- 22 players with an official free-throw attempt
- 1,776 attempts and 1,430 makes
- team and per-player summaries
- attempt-, trip-, and stint-level exports
- a static Analyst Workstation dashboard prototype

## View the dashboard

Open `index.html` locally, or use the GitHub Pages URL published from this repository.

## Project map

- `src/nba_ft/` — analysis and reporting package
- `tests/` — classifier, stint, pipeline, report, and end-to-end tests
- `output/warriors-2025-26/` — finalized team dataset and findings
- `output/curry-2025-26/` — Stephen Curry player analysis
- `output/jalen-brunson-2025-26/` — Jalen Brunson player analysis
- `mockups/` — Analyst Workstation interface
- `skill-development/nba-free-throw-analysis/` — reusable Codex skill
- `docs/superpowers/` — system design and implementation plans

## Run the tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Run a team analysis

```powershell
$env:PYTHONPATH = "src"
python -m nba_ft.team_cli --help
```

Downloaded ESPN responses live under `data/raw/` and are intentionally excluded from version control because they are reproducible caches and substantially duplicate the published analysis outputs.
