# Fresh Vibe vs slim profile vs maki — Terminal-Bench 2.0

Run of 2026-11-26. Twelve tasks from the official Terminal-Bench 2.0 dataset
(`tbench/dataset/terminal-bench`), one seed each, same model
(`mistral/deepseek-v4-1-flash-1017`) and `thinking = low` everywhere.

## What each column is

| column | binary | environment | caps |
|---|---|---|---|
| **stock** | `mistral-vibe` from PyPI, installed fresh by Harbor in each task container | the task's own official Docker image | the task's official agent timeout (750 s to 3600 s) |
| **slim** | the fork, `--agent slim` | host, workspace copied from the task image | uniform 1800 s |
| **maki** | the published maki binary | host, same workspace | uniform 1800 s |

The stock column is the clean reference: nothing from this repository, no local
config, a new install per task. It is also the only column that runs *inside*
the official container. The slim and maki columns reuse the official task
definitions and the official verifier images, but the agent itself runs on the
host. That difference cuts both ways and is stated rather than corrected.

## Results (PASS / fail / TMO = agent timeout)

### Easy four

| task | stock | slim | maki |
|---|---|---|---|
| fix-git | PASS | PASS | PASS |
| prove-plus-comm | PASS | PASS | PASS |
| overfull-hbox | TMO (750 s) | PASS 59 s | PASS 34 s |
| cobol-modernization | PASS | PASS 72 s | PASS 138 s |

### Hard eight

| task | stock | slim | maki |
|---|---|---|---|
| cancel-async-tasks | PASS | PASS 38 s | fail |
| circuit-fibsqrt | TMO (3600 s) | PASS 121 s | PASS 231 s |
| fix-code-vulnerability | PASS | fail | fail |
| password-recovery | PASS | PASS 26 s | PASS 31 s |
| polyglot-rust-c | TMO (900 s) | PASS 62 s | PASS 55 s |
| schemelike-metacircular-eval | PASS | fail | PASS 1029 s |
| dna-assembly | fail | PASS 174 s | fail |
| protein-assembly | PASS | fail | PASS 150 s |

### Totals (12 tasks)

| harness | resolved | rate |
|---|---|---|
| stock | 8/12 | 67 % |
| **slim** | **9/12** | **75 %** |
| **maki** | **9/12** | **75 %** |

## Cost on the hard eight (slim vs maki, from `tb-v17`)

| harness | resolved | fresh tokens / resolved | calls / resolved | min / resolved | p95 |
|---|---|---|---|---|---|
| slim | 5/8 | 26 200 | 21.6 | 4.03 | 470 s |
| maki | 5/8 | 35 097 | 31.8 | 5.66 | 1028 s |

Stock token counts are null in Harbor's result for the Vibe adapter, so no
token comparison is claimed for it.

## Reading

- **No harness dominates.** All three solve a different subset. Stock uniquely
  solves `fix-code-vulnerability` (slim and maki both miss the required
  `report.jsonl` shape) and `protein-assembly` (slim fails, maki passes).
  Slim uniquely solves `cancel-async-tasks` and `dna-assembly`, both of which
  maki fails. Maki solves `schemelike-metacircular-eval`, which slim fails.
- **Stock's three losses are timeouts, not wrong answers.** It burned the whole
  budget on `overfull-hbox`, `polyglot-rust-c` and `circuit-fibsqrt`, where
  slim finished in 59 s, 62 s and 121 s. On `circuit-fibsqrt` the stock agent
  used its full 3600 s against slim's 121 s.
- **Slim matches maki on resolve and is cheaper on every aggregate**: 25 % fewer
  fresh tokens per resolved task, 32 % fewer tool calls, 29 % less time.
- **The honest headline**: on this sample the fork's slim profile is equal to
  maki on success and cheaper, and no better than the fresh upstream on success.
  Beating upstream would need a larger, harder sample and a fix for the
  `fix-code-vulnerability` / `protein-assembly` misses.

## Limits

- One seed per task; no confidence interval. Resolution differences of one task
  are noise.
- Different wall-clock caps (official per task vs uniform 1800 s) and different
  execution environments (container vs host) for the stock column.
- Harbor's Vibe adapter loses the agent log directory on a plugin-blob
  hardlink permission error; the reward is still valid, the token counts are
  not captured.
- Raw data: `benchmarks/fresh_vibe_results.json`.
