# Harness benchmark history

Maki vs this fork, same model (`mistral/deepseek-v4-1-flash-1017`),
same prompts, fresh workspace per cell, mechanical verifiers.
Numbers are medians. `prompt` counts all prompt tokens (cached included); `effective`
counts only the uncached ones. Lower is better. Percentages are
relative to maki in the same run.

| run | commit | note | pass | time | prompt tok | effective tok | turns | vs maki (prompt / effective / time) |
|---|---|---|---|---|---|---|---|---|
| upstream-1 | `fb7511a` | upstream vibe, no changes (bugfix+csv, 1 attempt) | 2/2 vs 2/2 | 20.9s vs 4.8s | 79065 vs 19594 | 11481 vs 6346 | 0.0 vs 3.0 | +304% / +81% / +335% |
| upstream-2 | `fb7511a` | upstream vibe (expr, 2 attempts) | 2/2 vs 2/2 | 29.0s vs 13.1s | 108719 vs 35339 | 10031 vs 7307 | 9.0 vs 4.5 | +208% / +37% / +121% |
| slim-v1 | `13375bc` | maki prompt, 4 tools, no programmatic/subagents; TTL verifier was over-specified | 8/10 vs 8/10 | 17.9s vs 6.7s | 20608 vs 24610 | 4307 vs 6413 | 5.0 vs 3.5 | -16% / -33% / +167% |
| tuned-v2 | `f2d354d` | slim agent + maki prompt + efficiency rules | 10/10 vs 10/10 | 16.1s vs 7.5s | 18556 vs 23696 | 4556 vs 6563 | 4.0 vs 3.5 | -22% / -31% / +115% |
| ttl-fix | `f2d354d` | TTL verifier relaxed; both pass | 2/2 vs 2/2 | 20.0s vs 10.9s | 19949 vs 30838 | 4397 vs 6518 | 4.0 vs 4.0 | -35% / -33% / +83% |
| compressed-v3 | `a2d99d7` | compressed prompt and tool descriptions | 10/10 vs 10/10 | 13.0s vs 8.3s | 14602 vs 26026 | 4122 vs 6440 | 4.0 vs 4.0 | -44% / -36% / +57% |
| final-v4 | `3dbc70c` | compressed prompt, 3 attempts | 15/15 vs 15/15 | 13.6s vs 7.7s | 18723 vs 26976 | 4301 vs 6518 | 4 vs 4 | -31% / -34% / +77% |
| batch-tools-v5 | `04eac90` | read_files, index, glob, multiedit provided tools | 12/12 vs 12/12 | 12.0s vs 8.7s | 16634 vs 26930 | 4832 vs 6737 | 3.5 vs 4.0 | -38% / -28% / +38% |
| batch-tools-v6 | `6545a8c` | 6 tasks, 3 attempts, clean verifiers | 18/18 vs 18/18 | 11.8s vs 6.6s | 16024 vs 23549 | 4817 vs 6446 | 3.5 vs 3.5 | -32% / -25% / +79% |

Reproduce:

```bash
cd ../vibe_bench/harness_bench
VIBE_BIN=~/Projets/vibe-maki/.venv/bin/vibe \
  python3 run_bench.py --tasks bugfix csv_stats expr_eval ttl_cache merge_patch multi_fix --repeat 3
```
