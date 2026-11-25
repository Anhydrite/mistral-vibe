# Terminal-Bench tasks: maki vs this fork

Real Terminal-Bench tasks (Harbor cache): the agent works on a copy of
the task environment on the host, then the task's own tests run in the
task's own Docker image. Same model (`mistral/deepseek-v4-1-flash-1017`).
Medians over the attempts. Lower is better.

| run | commit | task | pass | maki s | vibe s | maki eff | vibe eff | verdict |
|---|---|---|---|---|---|---|---|---|
| tb-v1 | `0714c59` | fix-git | 3/3 vs 3/3 | 31.7 | 39.7 | 14914 | 13729 | maki (+25%) |
| tb-v1 | `0714c59` | prove-plus-comm | 3/3 vs 3/3 | 20.9 | 25.1 | 7926 | 5021 | maki (+20%) |
| tb-v2 | `012ea89` | cobol-modernization | 2/2 vs 2/2 | 200.0 | 158.8 | 33684 | 37546 | vibe (-21%) |
| tb-v2 | `012ea89` | fix-git | 2/2 vs 2/2 | 49.8 | 51.5 | 43670 | 13442 | maki (+3%) |
| tb-v2 | `012ea89` | overfull-hbox | 2/2 vs 2/2 | 104.8 | 108.3 | 18355 | 11284 | maki (+3%) |
| tb-v2 | `012ea89` | prove-plus-comm | 2/2 vs 2/2 | 18.4 | 30.2 | 8038 | 5780 | maki (+64%) |
| tb-v3 | `012ea89` | cobol-modernization | 2/2 vs 2/2 | 119.5 | 162.9 | 28852 | 24646 | maki (+36%) |
| tb-v3 | `012ea89` | fix-git | 2/2 vs 2/2 | 16.0 | 27.1 | 11462 | 11069 | maki (+69%) |
| tb-v3 | `012ea89` | overfull-hbox | 2/2 vs 1/2 | 31.7 | 87.7 | 11760 | 11904 | maki (+177%) |
| tb-v3 | `012ea89` | prove-plus-comm | 2/2 vs 2/2 | 14.5 | 11.1 | 7187 | 3138 | vibe (-23%) |
| tb-v4 | `48c18a4` | cobol-modernization | 3/3 vs 3/3 | 54.2 | 749.2 | 16932 | 31709 | maki (+1282%) |
| tb-v5 | `69f9ae0` | cobol-modernization | 2/3 vs 3/3 | 115.0 | 187.0 | 18123 | 30618 | maki (+63%) |
