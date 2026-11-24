# Mini API HTTP en bibliothèque standard

Dans le répertoire courant, crée `server.py`, un serveur HTTP JSON sans
dépendance externe.

## Lancement

```bash
python3 server.py --port 8123 --data data.json
```

Le serveur écoute sur `127.0.0.1` et persiste les items dans `data.json`
(créé si absent, JSON valide après chaque modification).

## Routes

- `GET /items` → `200`, JSON `[]` ou liste d'items.
- `POST /items` avec un corps JSON objet → `201`, renvoie l'item créé avec un
  champ `id` unique (entier ou chaîne). Corps invalide → `400`.
- `GET /items/<id>` → `200` avec l'item, ou `404`.
- `PATCH /items/<id>` avec un corps JSON objet → fusionne les champs, `200`,
  renvoie l'item mis à jour. Item absent → `404`, corps invalide → `400`.
- `DELETE /items/<id>` → `204` sans corps, ou `404`.
- Toute autre route → `404` avec un corps JSON `{"error": "not found"}`.

## Contraintes

- En-têtes `Content-Type: application/json` sur toutes les réponses JSON.
- Le serveur doit répondre à plusieurs requêtes successives sans redémarrer.
- Les identifiants sont uniques et stables pendant la vie du fichier.
- Aucune dépendance externe. Ne crée aucun autre fichier que `server.py`
  (le fichier de données est créé à l'exécution).
