from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _stat(name: str, rows: list[dict]) -> dict:
    makes = sum(bool(x.get("made")) for x in rows)
    attempts = len(rows)
    return {"split": name, "makes": makes, "attempts": attempts, "misses": attempts - makes,
            "pct": round(100 * makes / attempts, 1) if attempts else None}


def _workload_band(value, boundaries, labels):
    if value in (None, ""):
        return "unknown"
    number = float(value)
    if number <= boundaries[0]: return labels[0]
    if number <= boundaries[1]: return labels[1]
    return labels[2]


def build_splits(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    required = ["overall", "home", "away", "2 of 2 after made", "2 of 2 after missed",
                "immediate", "interrupted", "post-timeout", "post-review/challenge", "post-substitution"]
    for key in required: groups[key] = []
    for row in rows:
        groups["overall"].append(row)
        groups[str(row.get("venue", "unknown"))].append(row)
        groups[str(row.get("period_label", "unknown"))].append(row)
        groups[str(row.get("position", "unknown"))].append(row)
        groups[str(row.get("trip_type", "unknown"))].append(row)
        groups[str(row.get("score_state", "unknown"))].append(row)
        groups["clutch" if row.get("clutch") else "non-clutch"].append(row)
        groups["interrupted" if row.get("interrupted") else "immediate"].append(row)
        if row.get("timeout_before"): groups["post-timeout"].append(row)
        if row.get("review_before"): groups["post-review/challenge"].append(row)
        if row.get("substitution_before"): groups["post-substitution"].append(row)
        if int(row.get("attempt_number", 0)) == 2 and int(row.get("trip_length", 0)) == 2:
            groups[f"2 of 2 after {row.get('previous_result','unknown')}"] .append(row)
        stint = _workload_band(row.get("continuous_stint_seconds"), (300, 600), ("stint 0-5m", "stint 5-10m", "stint 10m+"))
        cumulative = _workload_band(row.get("cumulative_seconds_played"), (900, 1800), ("played 0-15m", "played 15-30m", "played 30m+"))
        groups[stint].append(row); groups[cumulative].append(row)
    return [_stat(name, values) for name, values in groups.items()]


def generate_findings(rows: list[dict], scope_name: str) -> list[dict]:
    split_map = {x["split"]: x for x in build_splits(rows)}
    findings = []
    overall = split_map["overall"]
    findings.append({"kind":"overall", "qualifier":f"Sample: {overall['attempts']} attempts",
        "text":f"{scope_name} made {overall['makes']}/{overall['attempts']} free throws ({overall['pct'] if overall['pct'] is not None else 'N/A'}%)."})
    for left, right, title in (
        ("1 of 2", "2 of 2", "first versus second of two"),
        ("2 of 2 after made", "2 of 2 after missed", "second shot by first-shot result"),
        ("home", "away", "home versus away"),
        ("immediate", "interrupted", "immediate versus interrupted"),
        ("stint 0-5m", "stint 10m+", "short versus long continuous stint"),
        ("played 0-15m", "played 30m+", "early versus high cumulative workload"),
    ):
        a, b = split_map.get(left, _stat(left, [])), split_map.get(right, _stat(right, []))
        if not a["attempts"] and not b["attempts"]:
            continue
        delta = None if a["pct"] is None or b["pct"] is None else round(b["pct"] - a["pct"], 1)
        delta_text = "not comparable" if delta is None else f"{delta:+.1f} percentage points for {right}"
        total = a["attempts"] + b["attempts"]
        qualifier = f"Sample: {a['attempts']} vs {b['attempts']} attempts; {'small sample, descriptive only' if min(a['attempts'], b['attempts']) < 10 else 'exploratory split'}"
        findings.append({"kind":title, "qualifier":qualifier,
            "text":f"{title.title()}: {left} {a['makes']}/{a['attempts']} ({a['pct'] if a['pct'] is not None else 'N/A'}%) versus {right} {b['makes']}/{b['attempts']} ({b['pct'] if b['pct'] is not None else 'N/A'}%); {delta_text}."})
    return findings


def _write_csv(path: Path, rows: list[dict]):
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(rows)


def _summary_markdown(title: str, splits: list[dict]) -> str:
    lines = [f"# {title}", "", "| Split | Makes | Attempts | Misses | FT% |", "|---|---:|---:|---:|---:|"]
    for item in splits:
        pct = "N/A" if item["pct"] is None else f"{item['pct']:.1f}%"
        lines.append(f"| {item['split']} | {item['makes']} | {item['attempts']} | {item['misses']} | {pct} |")
    return "\n".join(lines) + "\n"


def _findings_markdown(title: str, findings: list[dict]) -> str:
    lines = [f"# {title}", ""]
    for finding in findings:
        lines.extend([f"## {finding['kind'].title()}", "", finding["text"], "", f"_{finding['qualifier']}_", ""])
    return "\n".join(lines)


def write_team_outputs(attempts: list[dict], trips: list[dict], stints: list[dict], output: Path,
                       metadata: dict, validation: list[dict]):
    output.mkdir(parents=True, exist_ok=True)
    _write_csv(output / "free_throw_attempts.csv", attempts)
    _write_csv(output / "free_throw_trips.csv", trips)
    _write_csv(output / "stints.csv", stints)
    team_splits = build_splits(attempts)
    team_findings = generate_findings(attempts, metadata["team_name"])
    (output / "team-summary.md").write_text(_summary_markdown(f"{metadata['team_name']} Free Throws — {metadata['season']}", team_splits), encoding="utf-8")
    (output / "team-key-findings.md").write_text(_findings_markdown(f"{metadata['team_name']} Key Findings", team_findings), encoding="utf-8")
    player_payload = []
    by_player = defaultdict(list)
    for row in attempts: by_player[(row["player_id"], row["player_name"])].append(row)
    for (player_id, player_name), player_rows in sorted(by_player.items(), key=lambda x: x[0][1]):
        folder = output / "players" / _slug(player_name); folder.mkdir(parents=True, exist_ok=True)
        splits, findings = build_splits(player_rows), generate_findings(player_rows, player_name)
        (folder / "summary.md").write_text(_summary_markdown(f"{player_name} Free Throws — {metadata['season']}", splits), encoding="utf-8")
        (folder / "key-findings.md").write_text(_findings_markdown(f"{player_name} Key Findings", findings), encoding="utf-8")
        player_payload.append({"player_id":player_id, "player_name":player_name, "splits":splits, "findings":findings})
    dashboard = {"schema_version":"2.0", "metadata":metadata, "players":player_payload,
        "team_splits":team_splits, "team_findings":team_findings, "attempts":attempts,
        "trips":trips, "stints":stints, "validation":validation}
    (output / "dashboard.json").write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
