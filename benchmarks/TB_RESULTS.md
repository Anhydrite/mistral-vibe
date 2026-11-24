# Terminal-Bench tasks: maki vs this fork

Real Terminal-Bench tasks (Harbor cache): the agent works on a copy of
the task environment on the host, then the task's own tests run in the
task's own Docker image. Same model (`mistral/deepseek-v4-1-flash-1017`).
Medians over the attempts. Lower is better.

| run | commit | task | pass | maki s | vibe s | maki eff | vibe eff | verdict |
|---|---|---|---|---|---|---|---|---|
| tb-v1 | `0714c59` | fix-git | 3/3 vs 3/3 | 31.7 | 39.7 | 14914 | 13729 | maki (+25%) |
| tb-v1 | `0714c59` | prove-plus-comm | 3/3 vs 3/3 | 20.9 | 25.1 | 7926 | 5021 | maki (+20%) |
