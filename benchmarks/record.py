#!/usr/bin/env python3
"""Record a harness benchmark run in benchmarks/history.jsonl and RESULTS.md.

Consumes a results directory produced by vibe_bench/harness_bench/run_bench.py,
recomputes cache-aware token totals, and appends one record per run.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "benchmarks" / "history.jsonl"
RESULTS = ROOT / "benchmarks" / "RESULTS.md"


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def usage_of(cell: Path, harness: str) -> dict:
    if harness == "maki":
        try:
            for line in reversed((cell / "stdout.txt").read_text().splitlines()):
                if line.startswith("{") and '"type":"result"' in line:
                    u = json.loads(line)["usage"]
                    cached = u.get("cache_read_input_tokens", 0)
                    return {
                        "prompt": u["input_tokens"] + cached,
                        "cached": cached,
                        "effective": u["input_tokens"],
                        "output": u.get("output_tokens", 0),
                    }
        except Exception:
            pass
    else:
        try:
            u = json.loads((cell / "state/export/export.json").read_text())["usage"]
            cached = u.get("cached_input_tokens", 0)
            return {
                "prompt": u["input_tokens"],
                "cached": cached,
                "effective": u["input_tokens"] - cached,
                "output": u.get("output_tokens", 0),
            }
        except Exception:
            pass
    return {"prompt": 0, "cached": 0, "effective": 0, "output": 0}


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {}
    return {
        "n": len(rows),
        "passed": sum(1 for r in rows if r["passed"]),
        "mean_sec": round(statistics.mean(r["sec"] for r in rows), 1),
        "mean_prompt_tokens": round(statistics.mean(r["prompt"] for r in rows)),
        "mean_effective_tokens": round(statistics.mean(r["effective"] for r in rows)),
        "mean_turns": round(statistics.mean(r["turns"] for r in rows), 1),
        "median_sec": round(statistics.median(r["sec"] for r in rows), 1),
        "median_prompt_tokens": round(statistics.median(r["prompt"] for r in rows)),
        "median_effective_tokens": round(
            statistics.median(r["effective"] for r in rows)
        ),
        "median_turns": round(statistics.median(r["turns"] for r in rows), 1),
    }


def collect(results_dir: Path) -> tuple[list[dict], set[str], int]:
    rows, tasks = [], set()
    repeat = 0
    for result_path in sorted(results_dir.glob("*/result.json")):
        r = json.loads(result_path.read_text())
        if r.get("passed") is None:
            continue
        cell = result_path.parent
        u = usage_of(cell, r["harness"])
        tasks.add(r["task"])
        repeat = max(repeat, r.get("attempt", 1))
        rows.append(
            {
                "task": r["task"],
                "harness": r["harness"],
                "attempt": r.get("attempt", 1),
                "passed": bool(r["passed"]),
                "sec": r.get("elapsed_sec", 0),
                "turns": r.get("turns") or 0,
                **u,
            }
        )
    return rows, tasks, repeat


def pct(new: float, base: float) -> str:
    if not base:
        return "n/a"
    return f"{100 * (new - base) / base:+.0f}%"


def render_history(records: list[dict]) -> str:
    lines = [
        "# Harness benchmark history",
        "",
        "Maki vs this fork, same model (`mistral/deepseek-v4-1-flash-1017`),",
        "same prompts, fresh workspace per cell, mechanical verifiers.",
        "Numbers are medians. `prompt` counts all prompt tokens (cached included); `effective`",
        "counts only the uncached ones. Lower is better. Percentages are",
        "relative to maki in the same run.",
        "",
        "| run | commit | note | pass | time | prompt tok | effective tok | turns | vs maki (prompt / effective / time) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for rec in records:
        h = rec["harnesses"]
        m, v = h.get("maki", {}), h.get("vibe", {})
        if not m or not v:
            continue
        lines.append(
            "| {run} | `{commit}` | {note} | {vp}/{vn} vs {mp}/{mn} | "
            "{vt}s vs {mt}s | {vpt} vs {mpt} | {vet} vs {met} | "
            "{vtt} vs {mtt} | {pp} / {pe} / {ps} |".format(
                run=rec["run"],
                commit=rec["commit"],
                note=rec.get("note") or "",
                vp=v["passed"], vn=v["n"], mp=m["passed"], mn=m["n"],
                vt=v.get("median_sec", v["mean_sec"]),
                mt=m.get("median_sec", m["mean_sec"]),
                vpt=v.get("median_prompt_tokens", v["mean_prompt_tokens"]),
                mpt=m.get("median_prompt_tokens", m["mean_prompt_tokens"]),
                vet=v.get("median_effective_tokens", v["mean_effective_tokens"]),
                met=m.get("median_effective_tokens", m["mean_effective_tokens"]),
                vtt=v.get("median_turns", v["mean_turns"]),
                mtt=m.get("median_turns", m["mean_turns"]),
                pp=pct(
                    v.get("median_prompt_tokens", v["mean_prompt_tokens"]),
                    m.get("median_prompt_tokens", m["mean_prompt_tokens"]),
                ),
                pe=pct(
                    v.get("median_effective_tokens", v["mean_effective_tokens"]),
                    m.get("median_effective_tokens", m["mean_effective_tokens"]),
                ),
                ps=pct(
                    v.get("median_sec", v["mean_sec"]),
                    m.get("median_sec", m["mean_sec"]),
                ),
            )
        )
    lines += [
        "",
        "Reproduce:",
        "",
        "```bash",
        "cd ../vibe_bench/harness_bench",
        "VIBE_BIN=~/Projets/vibe-maki/.venv/bin/vibe \\",
        "  python3 run_bench.py --tasks bugfix csv_stats expr_eval ttl_cache merge_patch multi_fix --repeat 3",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", type=Path)
    ap.add_argument("--note", default="")
    ap.add_argument("--run", default=None)
    ap.add_argument("--commit", default=None)
    args = ap.parse_args()

    rows, tasks, repeat = collect(args.results_dir)
    if not rows:
        print("no results")
        return 1

    rec = {
        "run": args.run or args.results_dir.name,
        "date": datetime.now(timezone.utc).isoformat(),
        "commit": args.commit or git_commit(),
        "note": args.note,
        "model": "mistral/deepseek-v4-1-flash-1017",
        "tasks": sorted(tasks),
        "repeat": repeat,
        "results_dir": str(args.results_dir),
        "harnesses": {
            h: aggregate([r for r in rows if r["harness"] == h])
            for h in sorted({r["harness"] for r in rows})
        },
        "per_task": {
            f"{r['task']}__{r['harness']}__{r['attempt']}": {
                k: r[k] for k in ("passed", "sec", "turns", "prompt", "effective")
            }
            for r in rows
        },
    }

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    runs_dir = ROOT / "benchmarks" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{rec['run']}.json").write_text(
        json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    records = [json.loads(line) for line in HISTORY.read_text().splitlines() if line.strip()]
    RESULTS.write_text(render_history(records), encoding="utf-8")
    print(f"recorded {rec['run']}: {rec['harnesses']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
