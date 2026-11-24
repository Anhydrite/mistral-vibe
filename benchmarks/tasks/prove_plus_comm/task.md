# Prouver la commutativité de l'addition en Lean 4

Dans le répertoire courant, crée un fichier `Proof.lean` qui prouve :

```lean
theorem plus_comm (a b : Nat) : a + b = b + a
```

Le fichier doit compiler avec `lean Proof.lean` (code de sortie 0) et ne
contenir aucun avertissement d'erreur.

## Contraintes

- Aucun `sorry`, `admit`, `axiom` ni `native_decide`.
- La preuve doit être constructive : pas de `omega`, `decide` ni d'appel direct
  à un théorème de commutativité déjà fourni (`Nat.add_comm`,
  `Nat.add_comm'`, `add_comm`). Tu peux utiliser `induction` et les lemmes de
  réécriture de base (`Nat.add_succ`, `Nat.zero_add`, `Nat.succ_add`,
  `Nat.add_zero`).
- Un seul fichier créé : `Proof.lean`.
- Bibliothèque standard de Lean 4 uniquement, sans Mathlib.
