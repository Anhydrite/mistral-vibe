# Terminal-Bench : graphiques

12 runs, du tb-v1 au tb-instr.

Médianes par harnais ; les temps excluent les cellules non mesurées.

| harnais | cellules | réussite | temps médian | tokens facturés | lectures cache | coût médian | tours médians |
|---|---|---|---|---|---|---|---|
| maki | 72 | 97% (70/72) | 44 s | 17,651 | 121,024 | $0.011 | 13 |
| vibe | 72 | 96% (69/72) | 47 s | 13,968 | 70,528 | non rapporté | 10 |
| vibe@low | 8 | 100% (8/8) | 52 s | 18,804 | 111,168 | non rapporté | 12 |
| vibe@no-check | 8 | 100% (8/8) | 85 s | 15,284 | 66,176 | non rapporté | 10 |
| vibe@high | 3 | 100% (3/3) | 28 s | 12,371 | 64,000 | non rapporté | 11 |

## Taux de réussite par run

![Taux de réussite par run](01-reussite.png)

## Temps de travail par tâche

![Temps de travail par tâche](02-temps-par-tache.png)

## Tokens facturés par tâche

![Tokens facturés par tâche](03-tokens-par-tache.png)

## Lectures de cache par tâche

![Lectures de cache par tâche](04-cache-par-tache.png)

## Temps médian par run

![Temps médian par run](05-temps-par-run.png)

## maki vs vibe par tâche

![maki vs vibe par tâche](06-maki-vs-vibe.png)
