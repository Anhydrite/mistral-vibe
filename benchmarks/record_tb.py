#!/usr/bin/env python3
"""Record a Terminal-Bench run in benchmarks/tb_history.jsonl and TB_RESULTS.md."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "benchmarks" / "tb_history.jsonl"
RESULTS = ROOT / "benchmarks" / "TB_RESULTS.md"
CHARTS = ROOT / "benchmarks" / "charts"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plot_tb  # noqa: E402  (sibling script, imported for its chart builders)


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


def _usage(record: dict) -> dict[str, int]:
    """The token budgets of one attempt, cache reads kept apart.

    A cache read is billed and served far cheaper than a fresh prompt token,
    so a total that mixes them hides which harness really costs more. Every
    attempt reports ``prompt`` (all input tokens), ``cached`` (the cache reads
    inside it) and ``fresh`` (what was not cached).
    """
    given = record.get("input_tokens") or 0
    cached = record.get("cached_tokens") or 0
    if record["harness"].split("@")[0] == "maki":
        # Anthropic-style usage: input_tokens excludes the cache reads.
        return {"prompt": given + cached, "cached": cached, "fresh": given}
    # Mistral-style usage: input_tokens counts the cache reads it served.
    return {"prompt": given, "cached": cached, "fresh": max(given - cached, 0)}


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return round(ordered[index], 1)


def agg(records: list[dict]) -> dict:
    """The four metrics, always together: resolve rate, tokens, calls, time.

    A run that hit the time limit is censored: its cost is unknown, so it is
    left out of every average and only shows in the resolve rate.
    """
    usage = [_usage(r) for r in records if not r.get("timed_out")]
    measured = [r for r in records if not r.get("timed_out")]
    seconds = [r.get("work_sec", r["elapsed_sec"]) for r in measured]
    calls = [r.get("tool_calls") or 0 for r in measured]
    busies = [r["tool_sec"] for r in measured if r.get("tool_sec") is not None]
    passed = sum(1 for r in measured if r["passed"])
    resolved = passed or 1
    return {
        "n": len(records),
        "measured": len(measured),
        "passed": passed,
        "resolve_rate": round(passed / len(records), 3),
        "sum_prompt": sum(u["prompt"] for u in usage),
        "sum_cached": sum(u["cached"] for u in usage),
        "sum_effective": sum(u["fresh"] for u in usage),
        "sum_tool_calls": sum(calls),
        "sum_work_sec": round(sum(seconds), 1),
        # Cost per resolved task: every budget divided by what actually resolved.
        "tokens_per_resolved": round(sum(u["prompt"] for u in usage) / resolved),
        "cached_per_resolved": round(sum(u["cached"] for u in usage) / resolved),
        "fresh_per_resolved": round(sum(u["fresh"] for u in usage) / resolved),
        "calls_per_resolved": round(sum(calls) / resolved, 1),
        "minutes_per_resolved": round(sum(seconds) / 60 / resolved, 2),
        "median_sec": round(statistics.median(seconds), 1),
        "median_tool_sec": round(statistics.median(busies), 1) if busies else None,
        "tool_share": round(sum(busies) / sum(seconds), 3) if busies else None,
        "p95_sec": _p95(seconds),
        "median_effective": round(statistics.median(u["fresh"] for u in usage)),
        "median_cached": round(statistics.median(u["cached"] for u in usage)),
        "median_prompt": round(statistics.median(u["prompt"] for u in usage)),
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
    measured = [r for r in records if not r.get("timed_out")]
    passed = sum(1 for r in measured if r["passed"]) or 1
    usage = [_usage(r) for r in measured]
    seconds = [r.get("work_sec", r["elapsed_sec"]) for r in measured]
    calls = sum(r.get("tool_calls") or 0 for r in measured)
    busies = [r["tool_sec"] for r in measured if r.get("tool_sec") is not None]
    return {
        "resolve_rate": round(sum(1 for r in records if r["passed"]) / len(records), 3),
        "measured": len(measured),
        "tokens_per_resolved": round(sum(u["prompt"] for u in usage) / passed),
        "cached_per_resolved": round(sum(u["cached"] for u in usage) / passed),
        "fresh_per_resolved": round(sum(u["fresh"] for u in usage) / passed),
        "calls_per_resolved": round(calls / passed, 1),
        "minutes_per_resolved": round(sum(seconds) / 60 / passed, 2),
        "tool_minutes_per_resolved": (
            round(sum(busies) / 60 / passed, 2) if busies else None
        ),
        "tool_share": round(sum(busies) / sum(seconds), 3) if busies else None,
        "p95_sec": _p95(seconds),
    }


def refresh_charts(records: list[dict]) -> list[tuple[str, str]]:
    """Redraw benchmarks/charts from the recorded results dirs, named by run."""
    dirs = [Path(r.get("results_dir", "")) for r in records]
    roots = [d for d in dirs if d.is_dir()]
    if not roots:
        return []
    runs = plot_tb.load(roots)
    names = {Path(r["results_dir"]).name: r["run"] for r in records
             if Path(r.get("results_dir", "")).is_dir()}
    plot_tb.write_outputs(
        runs, plot_tb.harnesses_of(runs), CHARTS, png=True,
        titles=lambda name: names.get(name, plot_tb.label(name)),
    )
    return [(f"{stem}.png", title) for stem, title in plot_tb.chart_names()]


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
        "| run | commit | task | harness | resolve | median tok | median cache-read | median fresh | median calls | median tool s | median s | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    def rate(d: dict) -> float:
        return d.get("resolve_rate", round(d.get("passed", 0) / max(d.get("n", 1), 1), 3))

    for run in records:
        for task, by in sorted(run["per_task"].items()):
            base = by.get("maki")
            for harness, data in by.items():
                if base is None or harness == "maki":
                    verdict = "-"
                elif rate(data) != rate(base):
                    verdict = "vibe (resolve)" if rate(data) > rate(base) else "maki (resolve)"
                elif data.get("median_sec", 0) < base.get("median_sec", 0):
                    verdict = "vibe"
                else:
                    verdict = "maki"
                lines.append(
                    f"| {run['run']} | `{run['commit']}` | {task} | {harness} | "
                    f"{data['passed']}/{data['n']} | {data.get('median_prompt', 'n/a')} | "
                    f"{data.get('median_cached', 'n/a')} | "
                    f"{data.get('median_effective', 'n/a')} | "
                    f"{data.get('median_tool_calls', 0)} | "
                    f"{data.get('median_tool_sec') if data.get('median_tool_sec') is not None else 'n/a'} | "
                    f"{data.get('median_sec', 0)} | {verdict} |"
                )
    lines += [
        "",
        "## Cost per resolved task",
        "",
        "What a solved task really costs: all three budgets divided by the tasks",
        "that actually resolved, so a run that fails cheaply does not look good.",
        "",
        "| run | harness | resolve | tokens / resolved | cache-read / resolved | fresh / resolved | calls / resolved | tool min / resolved | minutes / resolved | tool share | p95 s |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run in records:
        for harness, data in (run.get("summary") or {}).items():
            lines.append(
                f"| {run['run']} | {harness} | {data['resolve_rate']:.0%} | "
                f"{data['tokens_per_resolved']} | {data.get('cached_per_resolved', 'n/a')} | "
                f"{data.get('fresh_per_resolved', 'n/a')} | {data['calls_per_resolved']} | "
                f"{data.get('tool_minutes_per_resolved', 'n/a')} | "
                f"{data['minutes_per_resolved']} | {data.get('tool_share', 'n/a')} | "
                f"{data['p95_sec']} |"
            )
    charts = [(name, title) for name, title in
              ((f"{stem}.png", title) for stem, title in plot_tb.chart_names())
              if (CHARTS / name).is_file()]
    if charts:
        lines += [
            "",
            "## Graphs",
            "",
            "One chart per question over every recorded run: pass rate, work time",
            "and uncached tokens per task, median time per run, and both harnesses",
            "against each other. `record_tb.py` redraws them here, and",
            "`python3 benchmarks/plot_tb.py` reproduces them alone.",
            "",
        ]
        for name, title in charts:
            lines += [f"![{title}](charts/{name})", ""]
    lines.append("")
    return "\n".join(lines)


def build_record(
    run: str, run_dir: Path, note: str, commit: str | None, model: str,
    date: str | None = None,
) -> dict:
    """One history entry, every metric recomputed from the raw attempts."""
    table = load(run_dir)
    return {
        "run": run,
        "date": date or datetime.now(timezone.utc).isoformat(),
        "commit": commit or "unknown",
        "note": note,
        "model": model,
        "results_dir": str(run_dir),
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
            for harness in sorted({h for by in table.values() for h in by})
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path, nargs="?")
    ap.add_argument("--run", default=None)
    ap.add_argument("--note", default="")
    ap.add_argument("--commit", default=None)
    ap.add_argument(
        "--refresh", action="store_true",
        help="recompute every history entry from its results dir",
    )
    args = ap.parse_args()

    if args.refresh:
        entries = [
            json.loads(line)
            for line in HISTORY.read_text().splitlines() if line.strip()
        ]
        rebuilt = []
        for entry in entries:
            run_dir = Path(entry.get("results_dir", ""))
            if not run_dir.is_dir():
                rebuilt.append(entry)
                continue
            rebuilt.append(build_record(
                entry["run"], run_dir, entry.get("note", ""),
                entry.get("commit"), entry.get("model"), entry.get("date"),
            ))
        HISTORY.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rebuilt))
        runs_dir = ROOT / "benchmarks" / "tb_runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        for entry in rebuilt:
            (runs_dir / f"{entry['run']}.json").write_text(
                json.dumps(entry, indent=2)
            )
        refresh_charts(rebuilt)
        RESULTS.write_text(render(rebuilt))
        print(f"refreshed {len(rebuilt)} runs")
        return 0

    if not args.run_dir or not args.run:
        raise SystemExit("run_dir and --run are required (or use --refresh)")
    record = build_record(
        args.run, args.run_dir, args.note, args.commit or commit(),
        "mistral/deepseek-v4-1-flash-1017",
    )
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    runs_dir = ROOT / "benchmarks" / "tb_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{args.run}.json").write_text(json.dumps(record, indent=2))
    records = [json.loads(l) for l in HISTORY.read_text().splitlines() if l.strip()]
    refresh_charts(records)
    RESULTS.write_text(render(records))
    print(json.dumps(record["per_task"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
