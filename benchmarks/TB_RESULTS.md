# Terminal-Bench tasks: maki vs this fork

Real Terminal-Bench tasks: the agent works on a copy of the built task
image, then the task's own tests run in that image. Same model
(`mistral/deepseek-v4-1-flash-1017`). Every row carries the four metrics
together: resolve, prompt tokens, tool calls, wall-clock work time
(harness startup excluded).

| run | commit | task | maki resolve | maki tok | maki calls | maki s | fork resolve | fork tok | fork calls | fork s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tb-v1 | `0714c59` | fix-git | 3/3 | 181314 | 0 | 31.7 | 3/3 | 123580 | 0 | 39.7 | maki |
| tb-v1 | `0714c59` | prove-plus-comm | 3/3 | 98422 | 0 | 20.9 | 3/3 | 58013 | 0 | 25.1 | maki |
| tb-v2 | `012ea89` | cobol-modernization | 2/2 | 1759124 | 0 | 200.0 | 2/2 | 1479082 | 0 | 158.8 | vibe |
| tb-v2 | `012ea89` | fix-git | 2/2 | 433814 | 0 | 49.8 | 2/2 | 167618 | 0 | 51.5 | maki |
| tb-v2 | `012ea89` | overfull-hbox | 2/2 | 279027 | 0 | 104.8 | 2/2 | 137108 | 0 | 108.3 | maki |
| tb-v2 | `012ea89` | prove-plus-comm | 2/2 | 80166 | 0 | 18.4 | 2/2 | 57940 | 0 | 30.2 | maki |
| tb-v3 | `012ea89` | cobol-modernization | 2/2 | 1303028 | 0 | 119.5 | 2/2 | 975494 | 0 | 162.9 | maki |
| tb-v3 | `012ea89` | fix-git | 2/2 | 93574 | 0 | 16.0 | 2/2 | 89277 | 0 | 27.1 | maki |
| tb-v3 | `012ea89` | overfull-hbox | 1/2 | 110448 | 0 | 31.7 | 2/2 | 110784 | 0 | 87.7 | vibe (resolve) |
| tb-v3 | `012ea89` | prove-plus-comm | 2/2 | 81875 | 0 | 14.5 | 2/2 | 12994 | 0 | 11.1 | vibe |
| tb-v4 | `48c18a4` | cobol-modernization | 3/3 | 279972 | 0 | 54.2 | 3/3 | 137693 | 0 | 749.2 | maki |
| tb-v5 | `69f9ae0` | cobol-modernization | 3/3 | 434485 | 0 | 115.0 | 2/3 | 237978 | 0 | 187.0 | maki (resolve) |
| tb-v6 | `eb7e3dd` | cobol-modernization | 3/3 | 553096 | 29 | 91.0 | 3/3 | 152566 | 11 | 192.6 | maki |
| tb-transfer-glm | `2e59bf8` | cobol-modernization | 0/1 | 1860956 | 47 | 672.6 | 0/1 | 0 | 0 | 338.8 | vibe |

## Cost per resolved task

What a solved task really costs: all three budgets divided by the tasks
that actually resolved, so a run that fails cheaply does not look good.

| run | harness | resolve | tokens / resolved | calls / resolved | minutes / resolved | p95 s |
|---|---|---|---|---|---|---|
| tb-v6 | maki | 100% | 1455374 | 37.7 | 2.71 | 367.5 |
| tb-v6 | vibe | 100% | 188140 | 11.0 | 3.79 | 356.6 |
| tb-transfer-glm | maki | 0% | 1860956 | 47.0 | 11.21 | 672.6 |
| tb-transfer-glm | vibe | 0% | 0 | 0.0 | 5.65 | 338.8 |
