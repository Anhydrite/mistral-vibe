#!/usr/bin/env python3
"""Record a Terminal-Bench run in benchmarks/tb_history.jsonl and TB_RESULTS.md."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "benchmarks" / "tb_history.jsonl"
RESULTS = ROOT / "benchmarks" / "TB_RESULTS.md"


def commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def load(run_dir: Path) -> dict[str, dict[str, list[dict]]]:
    table: dict[str, dict[str, list[dict]]] = {}
    for path in sorted(run_dir.glob("*/result.json")):
        record = json.loads(path.read_text())
        table.setdefault(record["task"], {}).setdefault(record["harness"], []).append(record)
    return table


def _usage(record: dict) -> tuple[int, int]:
    """(prompt tokens, uncached tokens) for one attempt."""
    given = record.get("input_tokens") or 0
    cached = record.get("cached_tokens") or 0
    if record["harness"] == "maki":
        return given + cached, given
    return given, max(given - cached, 0)


def agg(records: list[dict]) -> dict:
    pairs = [_usage(r) for r in records]
    return {
        "n": len(records),
        "passed": sum(1 for r in records if r["passed"]),
        "median_sec": round(statistics.median(r["elapsed_sec"] for r in records), 1),
        "median_effective": round(statistics.median(e for _, e in pairs)),
        "median_prompt": round(statistics.median(p for p, _ in pairs)),
        "median_turns": round(
            statistics.median(r.get("turns") or 0 for r in records), 1
        ),
    }


def pct(value: float, base: float) -> str:
    if not base:
        return "n/a"
    return f"{100 * (value - base) / base:+.0f}%"


def render(records: list[dict]) -> str:
    lines = [
        "# Terminal-Bench tasks: maki vs this fork",
        "",
        "Real Terminal-Bench tasks (Harbor cache): the agent works on a copy of",
        "the task environment on the host, then the task's own tests run in the",
        "task's own Docker image. Same model (`mistral/deepseek-v4-1-flash-1017`).",
        "Medians over the attempts. Lower is better.",
        "",
        "| run | commit | task | pass | maki s | vibe s | maki eff | vibe eff | verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for run in records:
        for task, by in sorted(run["per_task"].items()):
            m, v = by.get("maki"), by.get("vibe")
            if not m or not v:
                continue
            verdict = "vibe" if (v["median_sec"], v["median_effective"]) < (
                m["median_sec"], m["median_effective"]
            ) else "maki"
            lines.append(
                f"| {run['run']} | `{run['commit']}` | {task} | "
                f"{v['passed']}/{v['n']} vs {m['passed']}/{m['n']} | "
                f"{m['median_sec']} | {v['median_sec']} | {m['median_effective']} | "
                f"{v['median_effective']} | {verdict} "
                f"({pct(v['median_sec'], m['median_sec'])}) |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--run", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--commit", default=None)
    args = ap.parse_args()

    table = load(args.run_dir)
    record = {
        "run": args.run,
        "date": datetime.now(timezone.utc).isoformat(),
        "commit": args.commit or commit(),
        "note": args.note,
        "model": "mistral/deepseek-v4-1-flash-1017",
        "results_dir": str(args.run_dir),
        "per_task": {
            task: {h: agg(runs) for h, runs in by.items()}
            for task, by in table.items()
        },
    }
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    runs_dir = ROOT / "benchmarks" / "tb_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{args.run}.json").write_text(json.dumps(record, indent=2))
    records = [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()]
    RESULTS.write_text(render(records))
    print(json.dumps(record["per_task"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
