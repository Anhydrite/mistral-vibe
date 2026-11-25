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


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return round(ordered[index], 1)


def agg(records: list[dict]) -> dict:
    """The four metrics, always together: resolve rate, tokens, calls, time."""
    pairs = [_usage(r) for r in records]
    seconds = [r.get("work_sec", r["elapsed_sec"]) for r in records]
    calls = [r.get("tool_calls") or 0 for r in records]
    passed = sum(1 for r in records if r["passed"])
    resolved = passed or 1
    return {
        "n": len(records),
        "passed": passed,
        "resolve_rate": round(passed / len(records), 3),
        "sum_prompt": sum(p for p, _ in pairs),
        "sum_effective": sum(e for _, e in pairs),
        "sum_tool_calls": sum(calls),
        "sum_work_sec": round(sum(seconds), 1),
        # Cost per resolved task: all three, divided by what actually resolved.
        "tokens_per_resolved": round(sum(p for p, _ in pairs) / resolved),
        "calls_per_resolved": round(sum(calls) / resolved, 1),
        "minutes_per_resolved": round(sum(seconds) / 60 / resolved, 2),
        "median_sec": round(statistics.median(seconds), 1),
        "p95_sec": _p95(seconds),
        "median_effective": round(statistics.median(e for _, e in pairs)),
        "median_prompt": round(statistics.median(p for p, _ in pairs)),
        "median_turns": round(
            statistics.median(r.get("turns") or 0 for r in records), 1
        ),
        "median_tool_calls": round(statistics.median(calls), 1),
    }


def pct(value: float, base: float) -> str:
    if not base:
        return "n/a"
    return f"{100 * (value - base) / base:+.0f}%"


def _overall(records: list[dict]) -> dict:
    """The four metrics over every task of a run, cost per resolved task."""
    passed = sum(1 for r in records if r["passed"]) or 1
    pairs = [_usage(r) for r in records]
    seconds = [r.get("work_sec", r["elapsed_sec"]) for r in records]
    calls = sum(r.get("tool_calls") or 0 for r in records)
    return {
        "resolve_rate": round(sum(1 for r in records if r["passed"]) / len(records), 3),
        "tokens_per_resolved": round(sum(p for p, _ in pairs) / passed),
        "calls_per_resolved": round(calls / passed, 1),
        "minutes_per_resolved": round(sum(seconds) / 60 / passed, 2),
        "p95_sec": _p95(seconds),
    }


def render(records: list[dict]) -> str:
    lines = [
        "# Terminal-Bench tasks: maki vs this fork",
        "",
        "Real Terminal-Bench tasks: the agent works on a copy of the built task",
        "image, then the task's own tests run in that image. Same model",
        "(`mistral/deepseek-v4-1-flash-1017`). Every row carries the four metrics",
        "together: resolve, prompt tokens, tool calls, wall-clock work time",
        "(harness startup excluded).",
        "",
        "| run | commit | task | maki resolve | maki tok | maki calls | maki s | fork resolve | fork tok | fork calls | fork s | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run in records:
        for task, by in sorted(run["per_task"].items()):
            m, v = by.get("maki"), by.get("vibe")
            if not m or not v:
                continue
            def rate(d: dict) -> float:
                return d.get("resolve_rate", round(d.get("passed", 0) / max(d.get("n", 1), 1), 3))

            m_rate, v_rate = rate(m), rate(v)
            if v_rate > m_rate:
                verdict = "vibe (resolve)"
            elif v_rate < m_rate:
                verdict = "maki (resolve)"
            elif v.get("median_sec", 0) < m.get("median_sec", 0):
                verdict = "vibe"
            else:
                verdict = "maki"
            lines.append(
                f"| {run['run']} | `{run['commit']}` | {task} | "
                f"{m['passed']}/{m['n']} | {m.get('median_prompt', 0)} | "
                f"{m.get('median_tool_calls', 0)} | {m.get('median_sec', 0)} | "
                f"{v['passed']}/{v['n']} | {v.get('median_prompt', 0)} | "
                f"{v.get('median_tool_calls', 0)} | {v.get('median_sec', 0)} | {verdict} |"
            )
    lines += [
        "",
        "## Cost per resolved task",
        "",
        "What a solved task really costs: all three budgets divided by the tasks",
        "that actually resolved, so a run that fails cheaply does not look good.",
        "",
        "| run | harness | resolve | tokens / resolved | calls / resolved | minutes / resolved | p95 s |",
        "|---|---|---|---|---|---|---|",
    ]
    for run in records:
        for harness, data in (run.get("summary") or {}).items():
            lines.append(
                f"| {run['run']} | {harness} | {data['resolve_rate']:.0%} | "
                f"{data['tokens_per_resolved']} | {data['calls_per_resolved']} | "
                f"{data['minutes_per_resolved']} | {data['p95_sec']} |"
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
        "summary": {
            harness: _overall([
                record
                for by in table.values()
                for record in by.get(harness, [])
            ])
            for harness in ("maki", "vibe")
            if any(harness in by for by in table.values())
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
