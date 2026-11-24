# Refactor de calcul de prix

Le petit paquet `pricing/` calcule des prix TTC, mais les tests échouent et une
fonctionnalité manque.

```bash
python3 test_pricing.py
```

## À faire

Fais passer tous les tests sans modifier `test_pricing.py`.

Règles métier :

- `pricing.rates.tax_rate(country)` : `FR` → 0.20, `DE` → 0.19, `ES` → 0.21,
  toute autre valeur → 0.0. La casse est ignorée.
- `pricing.orders.total_cents(price_cents, qty, country)` : prix TTC arrondi à
  l'entier le plus proche.
- `pricing.orders.apply_discount(total_cents, code)` : `WELCOME10` applique
  -10 % et arrondit au centime le plus proche ; tout autre code lève
  `ValueError`.
- `pricing.invoices.invoice_total(lines, country)` : somme des lignes
  `(price_cents, qty)` puis application de la TVA du pays.

Contraintes :

- Ne modifie pas `test_pricing.py`.
- Conserve les noms et signatures publiques existants.
- La logique de taux ne doit exister qu'à un seul endroit : `pricing/rates.py`.
  `orders.py` et `invoices.py` doivent l'importer au lieu de dupliquer la table.
- Bibliothèque standard uniquement.
- Ne crée aucun nouveau fichier ; modifie les fichiers existants.
