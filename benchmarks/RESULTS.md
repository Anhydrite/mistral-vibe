# Harness benchmark history

Maki vs this fork, same model (`mistral/deepseek-v4-1-flash-1017`),
same prompts, fresh workspace per cell, mechanical verifiers.
`prompt` counts all prompt tokens (cached included); `effective`
counts only the uncached ones. Lower is better. Percentages are
relative to maki in the same run.

| run | commit | note | pass | time | prompt tok | effective tok | turns | vs maki (prompt / effective / time) |
|---|---|---|---|---|---|---|---|---|
| upstream-1 | `fb7511a` | upstream vibe, no changes (bugfix+csv, 1 attempt) | 2/2 vs 2/2 | 20.9s vs 4.8s | 79065 vs 19594 | 11481 vs 6346 | 0 vs 3 | +304% / +81% / +335% |
| upstream-2 | `fb7511a` | upstream vibe (expr, 2 attempts) | 2/2 vs 2/2 | 29.0s vs 13.1s | 108719 vs 35339 | 10031 vs 7307 | 9 vs 4.5 | +208% / +37% / +121% |
| slim-v1 | `13375bc` | maki prompt, 4 tools, no programmatic/subagents; TTL verifier was over-specified at the time | 8/10 vs 8/10 | 18.9s vs 8.0s | 25923 vs 24862 | 4816 vs 6494 | 5.2 vs 3.5 | +4% / -26% / +136% |
| tuned-v2 | `f2d354d` | slim agent + maki prompt + efficiency rules | 10/10 vs 10/10 | 16.2s vs 9.5s | 21324 vs 29083 | 5426 vs 6593 | 4.4 vs 3.9 | -27% / -18% / +71% |
| ttl-fix | `f2d354d` | TTL verifier relaxed; both harnesses pass | 2/2 vs 2/2 | 20.0s vs 10.9s | 19949 vs 30838 | 4397 vs 6518 | 4 vs 4 | -35% / -33% / +83% |

Reproduce:

```bash
cd ../vibe_bench/harness_bench
VIBE_BIN=~/Projets/vibe-maki/.venv/bin/vibe \
  python3 run_bench.py --tasks bugfix csv_stats expr_eval ttl_cache merge_patch --repeat 2
```
