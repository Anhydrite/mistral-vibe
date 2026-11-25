# Terminal-Bench tasks: maki vs this fork

Real Terminal-Bench tasks: the agent works on a copy of the built task
image, then the task's own tests run in that image. Same model
(`mistral/deepseek-v4-1-flash-1017`). Every row carries the four metrics
together: resolve, prompt tokens, tool calls, wall-clock work time
(harness startup excluded).

| run | commit | task | harness | resolve | median tok | median cache-read | median fresh | median calls | median tool s | median s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tb-v1 | `0714c59` | fix-git | maki | 3/3 | 181314 | 166400 | 14914 | 0 | n/a | 31.7 | - |
| tb-v1 | `0714c59` | fix-git | vibe | 3/3 | 123580 | 109696 | 13729 | 0 | n/a | 39.7 | maki |
| tb-v1 | `0714c59` | prove-plus-comm | maki | 3/3 | 98422 | 90496 | 7926 | 0 | n/a | 20.9 | - |
| tb-v1 | `0714c59` | prove-plus-comm | vibe | 3/3 | 58013 | 52992 | 5021 | 0 | n/a | 25.1 | maki |
| tb-v2 | `012ea89` | cobol-modernization | maki | 2/2 | 1759124 | 1725440 | 33684 | 0.0 | n/a | 200.0 | - |
| tb-v2 | `012ea89` | cobol-modernization | vibe | 2/2 | 1479082 | 1441536 | 37546 | 0.0 | n/a | 158.8 | vibe |
| tb-v2 | `012ea89` | fix-git | maki | 2/2 | 433814 | 390144 | 43670 | 0.0 | n/a | 49.8 | - |
| tb-v2 | `012ea89` | fix-git | vibe | 2/2 | 167618 | 154176 | 13442 | 0.0 | n/a | 51.5 | maki |
| tb-v2 | `012ea89` | overfull-hbox | maki | 2/2 | 279027 | 260672 | 18355 | 0.0 | n/a | 104.8 | - |
| tb-v2 | `012ea89` | overfull-hbox | vibe | 2/2 | 137108 | 125824 | 11284 | 0.0 | n/a | 108.3 | maki |
| tb-v2 | `012ea89` | prove-plus-comm | maki | 2/2 | 80166 | 72128 | 8038 | 0.0 | n/a | 18.4 | - |
| tb-v2 | `012ea89` | prove-plus-comm | vibe | 2/2 | 57940 | 52160 | 5780 | 0.0 | n/a | 30.2 | maki |
| tb-v3 | `012ea89` | cobol-modernization | maki | 2/2 | 1303028 | 1274176 | 28852 | 0.0 | n/a | 119.5 | - |
| tb-v3 | `012ea89` | cobol-modernization | vibe | 2/2 | 975494 | 950848 | 24646 | 0.0 | n/a | 162.9 | maki |
| tb-v3 | `012ea89` | fix-git | maki | 2/2 | 93574 | 82112 | 11462 | 0.0 | n/a | 16.0 | - |
| tb-v3 | `012ea89` | fix-git | vibe | 2/2 | 89277 | 78208 | 11069 | 0.0 | n/a | 27.1 | maki |
| tb-v3 | `012ea89` | overfull-hbox | maki | 1/2 | 110448 | 98688 | 11760 | 0.0 | n/a | 31.7 | - |
| tb-v3 | `012ea89` | overfull-hbox | vibe | 2/2 | 110784 | 98880 | 11904 | 0.0 | n/a | 87.7 | vibe (resolve) |
| tb-v3 | `012ea89` | prove-plus-comm | maki | 2/2 | 81875 | 74688 | 7187 | 0.0 | n/a | 14.5 | - |
| tb-v3 | `012ea89` | prove-plus-comm | vibe | 2/2 | 12994 | 9856 | 3138 | 0.0 | n/a | 11.1 | vibe |
| tb-v4 | `48c18a4` | cobol-modernization | maki | 3/3 | 279972 | 263040 | 16932 | 0 | n/a | 54.2 | - |
| tb-v4 | `48c18a4` | cobol-modernization | vibe | 3/3 | 137693 | 105984 | 31709 | 0 | n/a | 749.2 | maki |
| tb-v5 | `69f9ae0` | cobol-modernization | maki | 3/3 | 434485 | 420736 | 18123 | 0 | n/a | 115.0 | - |
| tb-v5 | `69f9ae0` | cobol-modernization | vibe | 2/3 | 237978 | 207360 | 30618 | 0 | n/a | 187.0 | maki (resolve) |
| tb-v6 | `eb7e3dd` | cobol-modernization | maki | 3/3 | 553096 | 535552 | 17544 | 29 | n/a | 91.0 | - |
| tb-v6 | `eb7e3dd` | cobol-modernization | vibe | 3/3 | 152566 | 125952 | 26614 | 11 | n/a | 192.6 | maki |
| tb-transfer-glm | `153f621` | cobol-modernization | maki | 0/1 | 1860956 | 1527552 | 333404 | 47 | n/a | 672.6 | - |
| tb-transfer-glm | `153f621` | cobol-modernization | vibe | 0/1 | 0 | 0 | 0 | 0 | n/a | 338.8 | vibe |

## Cost per resolved task

What a solved task really costs: all three budgets divided by the tasks
that actually resolved, so a run that fails cheaply does not look good.

| run | harness | resolve | tokens / resolved | cache-read / resolved | fresh / resolved | calls / resolved | tool min / resolved | minutes / resolved | tool share | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|
| tb-v1 | maki | 100% | 214668 | 201216 | 13452 | 0.0 | None | 0.85 | None | 193.5 |
| tb-v1 | vibe | 100% | 91400 | 82517 | 8883 | 0.0 | None | 0.52 | None | 44.9 |
| tb-v2 | maki | 100% | 638033 | 612096 | 25937 | 0.0 | None | 1.55 | None | 229.9 |
| tb-v2 | vibe | 100% | 460437 | 443424 | 17013 | 0.0 | None | 1.45 | None | 255.9 |
| tb-v3 | maki | 88% | 453978 | 437047 | 16932 | 0.0 | None | 0.87 | None | 180.9 |
| tb-v3 | vibe | 100% | 297137 | 284448 | 12689 | 0.0 | None | 1.2 | None | 282.2 |
| tb-v4 | maki | 100% | 272466 | 256981 | 15484 | 0.0 | None | 1.19 | None | 110.7 |
| tb-v4 | vibe | 100% | 292868 | 261973 | 30894 | 0.0 | None | 11.07 | None | 901.6 |
| tb-v5 | maki | 100% | 786993 | 768213 | 18780 | 0.0 | None | 2.6 | None | 240.7 |
| tb-v5 | vibe | 67% | 253367 | 221696 | 31671 | 0.0 | None | 10.49 | None | 901.7 |
| tb-v6 | maki | 100% | 1455374 | 1434411 | 20963 | 37.7 | None | 2.71 | None | 367.5 |
| tb-v6 | vibe | 100% | 188140 | 156672 | 31468 | 11.0 | None | 3.79 | None | 356.6 |
| tb-transfer-glm | maki | 0% | 1860956 | 1527552 | 333404 | 47.0 | None | 11.21 | None | 672.6 |
| tb-transfer-glm | vibe | 0% | 0 | 0 | 0 | 0.0 | None | 5.65 | None | 338.8 |
