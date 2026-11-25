# Terminal-Bench tasks: maki vs this fork

Real Terminal-Bench tasks: the agent works on a copy of the built task
image, then the task's own tests run in that image. Same model
(`mistral/deepseek-v4-1-flash-1017`). Every row carries the four metrics
together: resolve, prompt tokens, tool calls, wall-clock work time
(harness startup excluded).

| run | commit | task | harness | resolve | median tok | median cache-read | median fresh | median calls | median tool s | median harness s | median model s/turn | median s | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tb-v1 | `0714c59` | fix-git | maki | 3/3 | 181314 | 166400 | 14914 | 0 | n/a | n/a | n/a | 31.7 | - |
| tb-v1 | `0714c59` | fix-git | vibe | 3/3 | 123580 | 109696 | 13729 | 0 | n/a | n/a | n/a | 39.7 | maki |
| tb-v1 | `0714c59` | prove-plus-comm | maki | 3/3 | 98422 | 90496 | 7926 | 0 | n/a | n/a | n/a | 20.9 | - |
| tb-v1 | `0714c59` | prove-plus-comm | vibe | 3/3 | 58013 | 52992 | 5021 | 0 | n/a | n/a | n/a | 25.1 | maki |
| tb-v2 | `012ea89` | cobol-modernization | maki | 2/2 | 1759124 | 1725440 | 33684 | 0.0 | n/a | n/a | n/a | 200.0 | - |
| tb-v2 | `012ea89` | cobol-modernization | vibe | 2/2 | 1479082 | 1441536 | 37546 | 0.0 | n/a | n/a | n/a | 158.8 | vibe |
| tb-v2 | `012ea89` | fix-git | maki | 2/2 | 433814 | 390144 | 43670 | 0.0 | n/a | n/a | n/a | 49.8 | - |
| tb-v2 | `012ea89` | fix-git | vibe | 2/2 | 167618 | 154176 | 13442 | 0.0 | n/a | n/a | n/a | 51.5 | maki |
| tb-v2 | `012ea89` | overfull-hbox | maki | 2/2 | 279027 | 260672 | 18355 | 0.0 | n/a | n/a | n/a | 104.8 | - |
| tb-v2 | `012ea89` | overfull-hbox | vibe | 2/2 | 137108 | 125824 | 11284 | 0.0 | n/a | n/a | n/a | 108.3 | maki |
| tb-v2 | `012ea89` | prove-plus-comm | maki | 2/2 | 80166 | 72128 | 8038 | 0.0 | n/a | n/a | n/a | 18.4 | - |
| tb-v2 | `012ea89` | prove-plus-comm | vibe | 2/2 | 57940 | 52160 | 5780 | 0.0 | n/a | n/a | n/a | 30.2 | maki |
| tb-v3 | `012ea89` | cobol-modernization | maki | 2/2 | 1303028 | 1274176 | 28852 | 0.0 | n/a | n/a | n/a | 119.5 | - |
| tb-v3 | `012ea89` | cobol-modernization | vibe | 2/2 | 975494 | 950848 | 24646 | 0.0 | n/a | n/a | n/a | 162.9 | maki |
| tb-v3 | `012ea89` | fix-git | maki | 2/2 | 93574 | 82112 | 11462 | 0.0 | n/a | n/a | n/a | 16.0 | - |
| tb-v3 | `012ea89` | fix-git | vibe | 2/2 | 89277 | 78208 | 11069 | 0.0 | n/a | n/a | n/a | 27.1 | maki |
| tb-v3 | `012ea89` | overfull-hbox | maki | 1/2 | 110448 | 98688 | 11760 | 0.0 | n/a | n/a | n/a | 31.7 | - |
| tb-v3 | `012ea89` | overfull-hbox | vibe | 2/2 | 110784 | 98880 | 11904 | 0.0 | n/a | n/a | n/a | 87.7 | vibe (resolve) |
| tb-v3 | `012ea89` | prove-plus-comm | maki | 2/2 | 81875 | 74688 | 7187 | 0.0 | n/a | n/a | n/a | 14.5 | - |
| tb-v3 | `012ea89` | prove-plus-comm | vibe | 2/2 | 12994 | 9856 | 3138 | 0.0 | n/a | n/a | n/a | 11.1 | vibe |
| tb-v4 | `48c18a4` | cobol-modernization | maki | 3/3 | 279972 | 263040 | 16932 | 0 | n/a | n/a | n/a | 54.2 | - |
| tb-v4 | `48c18a4` | cobol-modernization | vibe | 3/3 | 137693 | 105984 | 31709 | 0 | n/a | n/a | n/a | 749.2 | maki |
| tb-v5 | `69f9ae0` | cobol-modernization | maki | 3/3 | 434485 | 420736 | 18123 | 0 | n/a | n/a | n/a | 115.0 | - |
| tb-v5 | `69f9ae0` | cobol-modernization | vibe | 2/3 | 237978 | 207360 | 30618 | 0 | n/a | n/a | n/a | 187.0 | maki (resolve) |
| tb-v6 | `eb7e3dd` | cobol-modernization | maki | 3/3 | 553096 | 535552 | 17544 | 29 | n/a | n/a | n/a | 91.0 | - |
| tb-v6 | `eb7e3dd` | cobol-modernization | vibe | 3/3 | 152566 | 125952 | 26614 | 11 | n/a | n/a | n/a | 192.6 | maki |
| tb-transfer-glm | `153f621` | cobol-modernization | maki | 0/1 | 1860956 | 1527552 | 333404 | 47 | n/a | n/a | n/a | 672.6 | - |
| tb-transfer-glm | `153f621` | cobol-modernization | vibe | 0/1 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 338.8 | vibe |
| tb-v7 | `3399387` | cobol-modernization | maki | 2/2 | 1574366 | 1536960 | 37406 | 35.5 | n/a | n/a | n/a | 238.9 | - |
| tb-v7 | `3399387` | cobol-modernization | vibe@low | 2/2 | 616172 | 595584 | 20588 | 25.0 | 9.3 | n/a | n/a | 124.4 | vibe |
| tb-v7 | `3399387` | cobol-modernization | vibe | 2/2 | 238302 | 222720 | 15582 | 16.0 | 5.4 | n/a | n/a | 79.3 | vibe |
| tb-v7 | `3399387` | fix-git | maki | 2/2 | 93784 | 81856 | 11928 | 12.0 | n/a | n/a | n/a | 16.9 | - |
| tb-v7 | `3399387` | fix-git | vibe@low | 2/2 | 60003 | 50624 | 9379 | 10.5 | 1.1 | n/a | n/a | 24.9 | maki |
| tb-v7 | `3399387` | fix-git | vibe | 2/2 | 65236 | 56064 | 9172 | 10.5 | 0.9 | n/a | n/a | 29.5 | maki |
| tb-v7 | `3399387` | overfull-hbox | maki | 2/2 | 321052 | 299584 | 21468 | 17.0 | n/a | n/a | n/a | 207.9 | - |
| tb-v7 | `3399387` | overfull-hbox | vibe@low | 2/2 | 218160 | 196224 | 21936 | 15.0 | 211.1 | n/a | n/a | 278.1 | maki |
| tb-v7 | `3399387` | overfull-hbox | vibe | 2/2 | 114474 | 99072 | 15402 | 12.0 | 276.0 | n/a | n/a | 314.2 | maki |
| tb-v7 | `3399387` | prove-plus-comm | maki | 2/2 | 33776 | 26880 | 6896 | 5.0 | n/a | n/a | n/a | 10.6 | - |
| tb-v7 | `3399387` | prove-plus-comm | vibe@low | 2/2 | 28199 | 23872 | 4327 | 6.5 | 1.3 | n/a | n/a | 19.9 | maki |
| tb-v7 | `3399387` | prove-plus-comm | vibe | 2/2 | 41108 | 36224 | 4884 | 8.0 | 1.6 | n/a | n/a | 24.4 | maki |
| tb-v8 | `a6e9337` | fix-git | maki | 3/3 | 80924 | 71168 | 10209 | 11 | n/a | n/a | n/a | 15.7 | - |
| tb-v8 | `a6e9337` | fix-git | vibe | 3/3 | 76761 | 67200 | 9561 | 13 | 1.4 | n/a | n/a | 30.1 | maki |
| tb-v8 | `a6e9337` | overfull-hbox | maki | 3/3 | 188410 | 173824 | 13661 | 13 | n/a | n/a | n/a | 127.2 | - |
| tb-v8 | `a6e9337` | overfull-hbox | vibe | 2/3 | 90556 | 71040 | 12351 | 9 | 53.3 | n/a | n/a | 119.5 | maki (resolve) |
| tb-v8 | `a6e9337` | prove-plus-comm | maki | 3/3 | 49751 | 42496 | 7255 | 6 | n/a | n/a | n/a | 23.7 | - |
| tb-v8 | `a6e9337` | prove-plus-comm | vibe | 3/3 | 18507 | 14848 | 3659 | 4 | 0.6 | n/a | n/a | 18.9 | vibe |
| tb-v9 | `e08d961` | cobol-modernization | maki | 2/2 | 250840 | 235392 | 15448 | 16.5 | n/a | n/a | n/a | 65.4 | - |
| tb-v9 | `e08d961` | cobol-modernization | vibe@no-check | 2/2 | 2303242 | 2261632 | 41610 | 42.0 | 17.7 | n/a | n/a | 259.3 | maki |
| tb-v9 | `e08d961` | cobol-modernization | vibe | 2/2 | 726582 | 696576 | 30006 | 20.5 | 5.4 | n/a | n/a | 140.3 | maki |
| tb-v9 | `e08d961` | fix-git | maki | 2/2 | 121828 | 110080 | 11748 | 14.5 | n/a | n/a | n/a | 28.5 | - |
| tb-v9 | `e08d961` | fix-git | vibe@no-check | 2/2 | 76450 | 66176 | 10274 | 12.0 | 1.5 | n/a | n/a | 29.4 | maki |
| tb-v9 | `e08d961` | fix-git | vibe | 2/2 | 59131 | 50624 | 8507 | 11.5 | 1.3 | n/a | n/a | 29.8 | maki |
| tb-v9 | `e08d961` | overfull-hbox | maki | 2/2 | 271748 | 248640 | 23108 | 15.5 | n/a | n/a | n/a | 135.3 | - |
| tb-v9 | `e08d961` | overfull-hbox | vibe@no-check | 2/2 | 129690 | 118400 | 11290 | 10.5 | 177.0 | n/a | n/a | 224.6 | maki |
| tb-v9 | `e08d961` | overfull-hbox | vibe | 2/2 | 171077 | 149824 | 21253 | 11.5 | 92.4 | n/a | n/a | 200.6 | maki |
| tb-v9 | `e08d961` | prove-plus-comm | maki | 2/2 | 64946 | 57920 | 7026 | 8.0 | n/a | n/a | n/a | 32.6 | - |
| tb-v9 | `e08d961` | prove-plus-comm | vibe@no-check | 2/2 | 34486 | 29696 | 4790 | 7.5 | 1.4 | n/a | n/a | 32.1 | vibe |
| tb-v9 | `e08d961` | prove-plus-comm | vibe | 2/2 | 68027 | 62784 | 5243 | 12.0 | 2.0 | n/a | n/a | 36.5 | maki |
| tb-v10 | `29acb07` | cobol-modernization | maki | 3/3 | 821093 | 794752 | 24723 | 29 | n/a | n/a | n/a | 233.6 | - |
| tb-v10 | `29acb07` | cobol-modernization | vibe | 3/3 | 790163 | 766464 | 23699 | 32 | 20.8 | n/a | n/a | 166.5 | vibe |
| tb-v10 | `29acb07` | fix-git | maki | 3/3 | 90681 | 79232 | 10201 | 10 | n/a | n/a | n/a | 18.8 | - |
| tb-v10 | `29acb07` | fix-git | vibe | 3/3 | 41588 | 36096 | 6881 | 8 | 1.0 | n/a | n/a | 22.0 | maki |
| tb-v10 | `29acb07` | overfull-hbox | maki | 3/3 | 150524 | 125056 | 13920 | 11 | n/a | n/a | n/a | 118.4 | - |
| tb-v10 | `29acb07` | overfull-hbox | vibe | 3/3 | 158841 | 145920 | 12704 | 12 | 5.5 | n/a | n/a | 64.9 | vibe |
| tb-v10 | `29acb07` | prove-plus-comm | maki | 3/3 | 90660 | 83328 | 7332 | 11 | n/a | n/a | n/a | 32.0 | - |
| tb-v10 | `29acb07` | prove-plus-comm | vibe | 3/3 | 31035 | 26880 | 4155 | 7 | 0.9 | n/a | n/a | 30.4 | vibe |
| tb-instr | `29acb07` | fix-git | maki | 3/3 | 74968 | 65536 | 9432 | 9 | 0.6 | 0.2 | 1.66 | 16.1 | - |
| tb-instr | `29acb07` | fix-git | vibe@high | 3/3 | 73304 | 64000 | 9304 | 13 | 1.0 | 6.8 | 2.28 | 27.8 | maki |
| tb-instr | `29acb07` | fix-git | vibe | 3/3 | 53509 | 44032 | 7124 | 7 | 0.5 | 6.2 | 2.41 | 26.2 | maki |
| tb-v12 | `144d098` | cobol-modernization | maki | 2/2 | 2390870 | 2363008 | 27862 | 50.5 | 102.3 | 102.0 | 4.24 | 316.8 | - |
| tb-v12 | `144d098` | cobol-modernization | vibe | 2/2 | 174970 | 159680 | 15290 | 13.5 | 6.7 | 13.2 | 3.72 | 61.6 | vibe |
| tb-v12 | `144d098` | fix-git | maki | 2/2 | 82639 | 72512 | 10127 | 11.5 | 0.2 | -0.1 | 1.32 | 12.8 | - |
| tb-v12 | `144d098` | fix-git | vibe | 2/2 | 48410 | 41344 | 7066 | 8.5 | 0.6 | 4.2 | 1.53 | 17.2 | maki |
| tb-v12 | `144d098` | overfull-hbox | maki | 2/2 | 155360 | 140736 | 14624 | 11.0 | 67.8 | 67.5 | 4.3 | 118.2 | - |
| tb-v12 | `144d098` | overfull-hbox | vibe | 2/2 | 178270 | 164032 | 14238 | 14.0 | 93.9 | 98.5 | 2.4 | 137.8 | maki |
| tb-v12 | `144d098` | prove-plus-comm | maki | 2/2 | 49846 | 42944 | 6902 | 6.5 | 0.6 | 0.4 | 1.8 | 12.9 | - |
| tb-v12 | `144d098` | prove-plus-comm | vibe | 2/2 | 50693 | 45824 | 4869 | 9.5 | 1.0 | 4.6 | 1.71 | 21.8 | maki |
| tb-v13 | `144d098` | cobol-modernization | maki | 2/2 | 463564 | 448064 | 15500 | 20.0 | 15.8 | 15.4 | 4.29 | 102.4 | - |
| tb-v13 | `144d098` | cobol-modernization | vibe@nohook | 2/2 | 1019848 | 995200 | 24648 | 33.0 | 0.0 | 5.4 | 5.06 | 172.2 | maki |
| tb-v13 | `144d098` | cobol-modernization | vibe@prog | 2/2 | 485972 | 467072 | 18900 | 20.0 | 5.4 | 13.3 | 4.65 | 103.4 | maki |
| tb-v13 | `144d098` | cobol-modernization | vibe | 2/2 | 257806 | 240960 | 16846 | 15.0 | 5.8 | 12.6 | 3.61 | 68.0 | vibe |
| tb-v13 | `144d098` | fix-git | maki | 2/2 | 93461 | 82816 | 10645 | 10.5 | 0.3 | -0.0 | 1.45 | 15.0 | - |
| tb-v13 | `144d098` | fix-git | vibe@nohook | 2/2 | 35636 | 29184 | 6452 | 6.5 | 0.0 | 5.0 | 1.68 | 17.4 | maki |
| tb-v13 | `144d098` | fix-git | vibe@prog | 2/2 | 75128 | 65920 | 9208 | 9.0 | 1.2 | 6.7 | 1.22 | 18.9 | maki |
| tb-v13 | `144d098` | fix-git | vibe | 2/2 | 45739 | 38592 | 7147 | 9.0 | 0.8 | 6.7 | 1.19 | 17.0 | maki |
| tb-v13 | `144d098` | overfull-hbox | maki | 2/2 | 174008 | 158592 | 15416 | 15.0 | 111.4 | 111.0 | 2.33 | 142.7 | - |
| tb-v13 | `144d098` | overfull-hbox | vibe@nohook | 2/2 | 63268 | 52992 | 10276 | 7.0 | 0.0 | 5.8 | 5.39 | 48.9 | vibe |
| tb-v13 | `144d098` | overfull-hbox | vibe@prog | 2/2 | 106534 | 93504 | 13030 | 9.0 | 130.1 | 135.4 | 3.53 | 164.8 | maki |
| tb-v13 | `144d098` | overfull-hbox | vibe | 2/2 | 62607 | 52160 | 10447 | 6.5 | 14.1 | 20.1 | 3.66 | 45.7 | vibe |
| tb-v13 | `144d098` | prove-plus-comm | maki | 2/2 | 66558 | 59584 | 6974 | 7.5 | 2.1 | 1.7 | 1.91 | 19.1 | - |
| tb-v13 | `144d098` | prove-plus-comm | vibe@nohook | 2/2 | 19262 | 15360 | 3902 | 4.0 | 0.0 | 5.4 | 1.99 | 15.6 | vibe |
| tb-v13 | `144d098` | prove-plus-comm | vibe@prog | 2/2 | 92306 | 84480 | 7826 | 10.0 | 2.4 | 8.2 | 1.96 | 31.6 | maki |
| tb-v13 | `144d098` | prove-plus-comm | vibe | 2/2 | 45982 | 41152 | 4830 | 9.0 | 1.8 | 7.3 | 2.04 | 27.8 | maki |
| tb-v14 | `642e057` | cobol-modernization | maki | 2/2 | 1025786 | 1002560 | 23226 | 33.0 | 72.6 | 72.2 | 3.78 | 204.5 | - |
| tb-v14 | `642e057` | cobol-modernization | vibe | 2/2 | 176104 | 163392 | 12712 | 12.5 | 7.0 | 12.3 | 3.65 | 58.2 | vibe |
| tb-v14 | `642e057` | fix-git | maki | 2/2 | 76832 | 67136 | 9696 | 10.5 | 0.5 | 0.1 | 1.32 | 12.5 | - |
| tb-v14 | `642e057` | fix-git | vibe | 2/2 | 53949 | 43712 | 10237 | 8.5 | 0.6 | 5.8 | 1.62 | 21.2 | maki |
| tb-v14 | `642e057` | overfull-hbox | maki | 2/2 | 122232 | 108096 | 14136 | 10.5 | 26.9 | 26.5 | 2.33 | 49.8 | - |
| tb-v14 | `642e057` | overfull-hbox | vibe | 2/2 | 89564 | 77696 | 11868 | 8.5 | 80.2 | 86.0 | 2.54 | 110.1 | maki |
| tb-v14 | `642e057` | prove-plus-comm | maki | 2/2 | 90960 | 83392 | 7568 | 11.0 | 1.5 | 1.1 | 2.44 | 28.7 | - |
| tb-v14 | `642e057` | prove-plus-comm | vibe | 2/2 | 22246 | 17920 | 4326 | 4.0 | 0.8 | 5.8 | 1.97 | 16.7 | vibe |
| tb-v15 | `f387947` | mvcc-lsm-compaction | maki | 0/3 | 170879 | 152704 | 18175 | 12 | 20.7 | 20.3 | 4.02 | 67.9 | - |
| tb-v15 | `f387947` | mvcc-lsm-compaction | vibe | 1/3 | 101600 | 88960 | 12640 | 8 | 20.4 | 25.4 | 1.83 | 41.8 | vibe (resolve) |
| tb-v16 | `1bd954f` | cobol-modernization | maki | 2/2 | 657422 | 637888 | 19534 | 28.0 | 43.5 | 43.2 | 3.18 | 131.2 | - |
| tb-v16 | `1bd954f` | cobol-modernization | vibe-classic | 2/2 | 1759607 | 1715520 | 44087 | 37.5 | 16.8 | 20.8 | 3.45 | 152.1 | maki |
| tb-v16 | `1bd954f` | cobol-modernization | vibe-custom | 2/2 | 226917 | 209792 | 17125 | 13.5 | 2.2 | 5.8 | 4.42 | 64.6 | vibe |
| tb-v16 | `1bd954f` | fix-git | maki | 2/2 | 113503 | 103680 | 9823 | 12.0 | 0.2 | -0.1 | 0.89 | 11.7 | - |
| tb-v16 | `1bd954f` | fix-git | vibe-classic | 2/2 | 173749 | 158464 | 15285 | 12.5 | 0.8 | 4.4 | 1.61 | 24.8 | maki |
| tb-v16 | `1bd954f` | fix-git | vibe-custom | 2/2 | 39708 | 32832 | 6876 | 6.5 | 0.5 | 3.8 | 2.61 | 23.9 | maki |
| tb-v16 | `1bd954f` | overfull-hbox | maki | 2/2 | 163802 | 151296 | 12506 | 13.5 | 7.1 | 6.9 | 2.96 | 43.6 | - |
| tb-v16 | `1bd954f` | overfull-hbox | vibe-classic | 2/2 | 366394 | 345152 | 21242 | 18.5 | 15.1 | 19.0 | 1.89 | 54.6 | maki |
| tb-v16 | `1bd954f` | overfull-hbox | vibe-custom | 1/2 | 187118 | 174400 | 12718 | 14.0 | 21.0 | 24.7 | 2.55 | 64.1 | maki (resolve) |
| tb-v16 | `1bd954f` | prove-plus-comm | maki | 2/2 | 56678 | 49344 | 7334 | 7.0 | 0.5 | 0.2 | 1.89 | 14.7 | - |
| tb-v16 | `1bd954f` | prove-plus-comm | vibe-classic | 2/2 | 153649 | 140160 | 13489 | 12.0 | 1.6 | 5.2 | 1.53 | 23.5 | maki |
| tb-v16 | `1bd954f` | prove-plus-comm | vibe-custom | 2/2 | 28696 | 24128 | 4568 | 5.0 | 0.9 | 4.5 | 1.53 | 14.7 | maki |

## Cost per resolved task

What a solved task really costs: all three budgets divided by the tasks
that actually resolved, so a run that fails cheaply does not look good.

| run | harness | resolve | tokens / resolved | cache-read / resolved | fresh / resolved | calls / resolved | tool min / resolved | harness min / resolved | model min / resolved | minutes / resolved | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tb-v1 | maki | 100% | 214668 | 201216 | 13452 | 0.0 | None | None | 0.85 | 0.85 | 193.5 |
| tb-v1 | vibe | 100% | 91400 | 82517 | 8883 | 0.0 | None | None | 0.52 | 0.52 | 44.9 |
| tb-v2 | maki | 100% | 638033 | 612096 | 25937 | 0.0 | None | None | 1.55 | 1.55 | 229.9 |
| tb-v2 | vibe | 100% | 460437 | 443424 | 17013 | 0.0 | None | None | 1.45 | 1.45 | 255.9 |
| tb-v3 | maki | 88% | 453978 | 437047 | 16932 | 0.0 | None | None | 0.87 | 0.87 | 180.9 |
| tb-v3 | vibe | 100% | 297137 | 284448 | 12689 | 0.0 | None | None | 1.2 | 1.2 | 282.2 |
| tb-v4 | maki | 100% | 272466 | 256981 | 15484 | 0.0 | None | None | 1.19 | 1.19 | 110.7 |
| tb-v4 | vibe | 100% | 292868 | 261973 | 30894 | 0.0 | None | None | 11.07 | 11.07 | 901.6 |
| tb-v5 | maki | 100% | 786993 | 768213 | 18780 | 0.0 | None | None | 2.6 | 2.6 | 240.7 |
| tb-v5 | vibe | 67% | 253367 | 221696 | 31671 | 0.0 | None | None | 10.49 | 10.49 | 901.7 |
| tb-v6 | maki | 100% | 1455374 | 1434411 | 20963 | 37.7 | None | None | 2.71 | 2.71 | 367.5 |
| tb-v6 | vibe | 100% | 188140 | 156672 | 31468 | 11.0 | None | None | 3.79 | 3.79 | 356.6 |
| tb-transfer-glm | maki | 0% | 1860956 | 1527552 | 333404 | 47.0 | None | None | 11.21 | 11.21 | 672.6 |
| tb-transfer-glm | vibe | 0% | 0 | 0 | 0 | 0.0 | None | None | 5.65 | 5.65 | 338.8 |
| tb-v7 | maki | 100% | 505744 | 486320 | 19424 | 17.4 | None | None | 1.98 | 1.98 | 403.1 |
| tb-v7 | vibe | 100% | 114780 | 103520 | 11260 | 11.6 | 1.18 | None | 1.86 | 1.86 | 400.5 |
| tb-v7 | vibe@low | 100% | 230633 | 216576 | 14057 | 14.2 | 0.93 | None | 1.86 | 1.86 | 430.7 |
| tb-v8 | maki | 100% | 108793 | 98446 | 10347 | 10.8 | None | None | 1.13 | 1.13 | 250.6 |
| tb-v8 | vibe | 89% | 80146 | 69936 | 10210 | 10.4 | 0.88 | None | 1.46 | 1.46 | 372.8 |
| tb-v9 | maki | 100% | 177340 | 163008 | 14332 | 13.6 | None | None | 1.09 | 1.09 | 146.0 |
| tb-v9 | vibe | 100% | 256204 | 239952 | 16252 | 13.9 | 0.42 | None | 1.7 | 1.7 | 243.9 |
| tb-v9 | vibe@no-check | 100% | 635967 | 618976 | 16991 | 18.0 | 0.82 | None | 2.27 | 2.27 | 382.7 |
| tb-v10 | maki | 100% | 345377 | 330592 | 14785 | 17.3 | None | None | 1.75 | 1.75 | 243.8 |
| tb-v10 | vibe | 100% | 241009 | 229749 | 11260 | 13.8 | 0.16 | None | 1.17 | 1.17 | 166.5 |
| tb-instr | maki | 100% | 73290 | 63744 | 9546 | 10.0 | 0.01 | 0.0 | 0.26 | 0.26 | 16.9 |
| tb-instr | vibe | 100% | 48312 | 40576 | 7736 | 7.7 | 0.01 | 0.09 | 0.34 | 0.43 | 33.2 |
| tb-instr | vibe@high | 100% | 80990 | 70784 | 10206 | 13.0 | 0.02 | 0.11 | 0.4 | 0.51 | 39.4 |
| tb-v12 | maki | 100% | 669679 | 654800 | 14879 | 19.9 | 0.71 | 0.71 | 1.21 | 1.92 | 544.6 |
| tb-v12 | vibe | 100% | 113086 | 102720 | 10366 | 11.4 | 0.43 | 0.5 | 0.49 | 0.99 | 252.2 |
| tb-v13 | maki | 100% | 199398 | 187264 | 12134 | 13.2 | 0.54 | 0.53 | 0.63 | 1.16 | 163.8 |
| tb-v13 | vibe | 100% | 103034 | 93216 | 9818 | 9.9 | 0.09 | 0.19 | 0.47 | 0.66 | 89.4 |
| tb-v13 | vibe@nohook | 100% | 284503 | 273184 | 11319 | 12.6 | 0.0 | 0.09 | 0.97 | 1.06 | 222.6 |
| tb-v13 | vibe@prog | 100% | 189985 | 177744 | 12241 | 12.0 | 0.58 | 0.68 | 0.65 | 1.33 | 220.0 |
| tb-v14 | maki | 100% | 328952 | 315296 | 13656 | 16.2 | 0.42 | 0.42 | 0.81 | 1.23 | 341.9 |
| tb-v14 | vibe | 100% | 85466 | 75680 | 9786 | 8.4 | 0.37 | 0.46 | 0.4 | 0.86 | 113.4 |
| tb-v15 | maki | 0% | 611223 | 558464 | 52759 | 41.0 | 1.03 | 1.01 | 2.52 | 3.53 | 83.4 |
| tb-v15 | vibe | 33% | 292049 | 254080 | 37969 | 26.0 | 0.97 | 1.24 | 1.16 | 2.4 | 66.6 |
| tb-v16 | maki | 100% | 247851 | 235552 | 12299 | 15.1 | 0.21 | 0.21 | 0.63 | 0.84 | 137.4 |
| tb-v16 | vibe-classic | 100% | 613350 | 589824 | 23526 | 20.1 | 0.14 | 0.21 | 0.85 | 1.06 | 155.4 |
| tb-v16 | vibe-custom | 88% | 137840 | 126043 | 11797 | 11.1 | 0.12 | 0.18 | 0.62 | 0.8 | 72.0 |

## Graphs

One chart per question over every recorded run: pass rate, work time,
billed tokens and cache reads per task, median time per run, and both
harnesses against each other. Tokens are normalised first, since the
two CLIs count cache reads differently. `record_tb.py` redraws the
charts here, and `python3 benchmarks/plot_tb.py` reproduces them alone.

![Taux de réussite par run](charts/01-reussite.png)

![Temps de travail par tâche](charts/02-temps-par-tache.png)

![Tokens facturés par tâche](charts/03-tokens-par-tache.png)

![Lectures de cache par tâche](charts/04-cache-par-tache.png)

![Temps médian par run](charts/05-temps-par-run.png)

![maki vs vibe par tâche](charts/06-maki-vs-vibe.png)

