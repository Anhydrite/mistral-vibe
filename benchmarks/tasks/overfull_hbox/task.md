# Rendre la notice compilable sans overfull \hbox

Le fichier `report.tex` compile, mais le log de `pdflatex` signale des
`Overfull \hbox` : du texte dépasse dans la marge. La CI refuse toute
avertissement de ce type.

## Objectif

Modifier `report.tex` pour que `pdflatex` compile **sans aucun**
`Overfull \hbox` **ni aucun** `Underfull \hbox (badness 10000)`.

## Contraintes

- Ne change pas le texte visible : toutes les phrases et l'URL doivent rester
  identiques au caractère près (tu peux ajouter des commandes de mise en forme
  autour, pas réécrire le contenu).
- Le document doit rester un seul PDF valide, produit par :
  `pdflatex -interaction=nonstopmode report.tex`
- Ne supprime pas de section ni de paragraphe.
- N'ajoute aucun autre fichier que ceux produits par LaTeX (`.aux`, `.log`,
  `.pdf`).
