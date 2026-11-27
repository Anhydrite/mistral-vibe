# KV store transactionnel persistant

Dans le répertoire courant, crée `kvstore.py` exposant une classe `KVStore`.

## Interface

```python
KVStore(path: str | None = None)
```

- `get(key)` : valeur ou `None`.
- `set(key, value)` : écrit une valeur JSON-sérialisable.
- `delete(key)` : supprime la clé (sans erreur si absente).
- `values()` : dict trié des clés/valeurs courantes.
- `begin()` : ouvre une transaction ; les transactions peuvent être imbriquées.
- `commit()` : valide la transaction la plus interne.
- `rollback()` : annule les changements de la transaction la plus interne.
- `snapshot()` : renvoie un jeton opaque représentant l'état courant.
- `restore(token)` : revient à l'état capturé par ce jeton, en annulant les
  transactions ouvertes.
- `commit()` ou `rollback()` sans transaction ouverte lève `RuntimeError`.
- `restore()` avec un jeton inconnu lève `ValueError`.

## Règles

- Les changements d'une transaction interne ne sont visibles qu'à l'intérieur de
  celle-ci et de ses transactions parentes, jamais après un `rollback`.
- Un `commit` de la transaction la plus externe matérialise l'état sur disque
  si `path` est fourni. Le fichier doit être du JSON valide à tout moment
  (écriture atomique).
- Une nouvelle instance `KVStore(path)` recharge l'état sauvegardé.
- `values()` renvoie une copie : la modifier ne change pas le store.
- Aucune dépendance externe. Ne crée aucun autre fichier que `kvstore.py`.
