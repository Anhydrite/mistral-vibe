# Moderniser un programme COBOL en Python

`legacy/sales.cob` est le programme COBOL qui produit l'état des ventes. Il
lit un fichier texte (`sales.txt`, passé en argument) et écrit le rapport sur
stdout. La machine ne peut plus exécuter de COBOL : il faut réécrire la même
logique en Python.

## Objectif

Créer `sales.py` à la racine du répertoire courant, utilisé ainsi :

```bash
python3 sales.py sales.txt
```

Il doit produire **exactement** la même sortie que le programme COBOL : même
ordre des lignes, même format, mêmes arrondis.

## Règles métier (tirées du source)

- Un enregistrement par ligne, champs séparés par des espaces :
  `REGION ITEM QUANTITY UNIT_PRICE`.
- Montant d'une ligne = `quantity * unit_price`, arrondi à 2 décimales
  (arrondi commercial, demi vers le haut).
- Si `quantity >= 10`, une remise de 5 % s'applique au montant de la ligne,
  arrondie à 2 décimales.
- Les lignes sont regroupées par région ; à chaque changement de région le
  programme imprime le sous-total de la région.
- À la fin : total général, puis la taxe de 8,25 % arrondie à 2 décimales, puis
  le total taxé.

## Contraintes

- Bibliothèque standard uniquement.
- Ne modifie pas `legacy/sales.cob` ni les fichiers `.txt` fournis.
- Ne crée aucun autre fichier que `sales.py`.
- Les jeux d'essai fournis (`sales.txt`, `expected.txt`) donnent la forme
  exacte attendue.
