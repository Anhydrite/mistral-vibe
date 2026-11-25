# Terminal-Bench : graphiques

10 runs, du tb-v1 au tb-v9.

Médianes par harnais ; les temps excluent les cellules non mesurées.

| harnais | cellules | réussite | temps médian | tokens facturés | lectures cache | coût médian | tours médians |
|---|---|---|---|---|---|---|---|
| maki | 57 | 96% (55/57) | 48 s | 19,314 | 143,360 | $0.011 | 14 |
| vibe | 57 | 95% (54/57) | 52 s | 15,432 | 75,136 | non rapporté | 10 |
| vibe@low | 8 | 100% (8/8) | 52 s | 18,804 | 111,168 | non rapporté | 12 |
| vibe@no-check | 8 | 100% (8/8) | 85 s | 15,284 | 66,176 | non rapporté | 10 |

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
