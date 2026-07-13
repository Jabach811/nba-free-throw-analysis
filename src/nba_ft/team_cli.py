import argparse
import json
from pathlib import Path

from .team_pipeline import run_team


def main():
    parser = argparse.ArgumentParser(description="Analyze every official free throw for one NBA team-season.")
    parser.add_argument("--team-id", required=True, help="ESPN team ID")
    parser.add_argument("--team-slug", required=True, help="ESPN team abbreviation, e.g. gs")
    parser.add_argument("--team-name", required=True)
    parser.add_argument("--season-end-year", type=int, required=True)
    parser.add_argument("--work-dir", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = run_team(args.work_dir, args.team_id, args.team_slug, args.team_name, args.season_end_year, args.output)
    print(json.dumps(manifest, indent=2))
    raise SystemExit(0 if manifest["complete"] else 1)


if __name__ == "__main__":
    main()
