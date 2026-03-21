# TAG Express PYTHON APP - Calculateur d'Itinéraires

Application Python/Tkinter pour rechercher des trajets dans le réseau MTAG dans le but d'en faire un siteweb axé téléphone plus tard.

## Fonctionnalités

- Recherche d'itinéraires entre deux arrêts TAG de la MÊME LIGNE ! Les correspondances ne sont pas encore au point.
- Vérification d'arrêt via cache (clusters par ligne + arrêts manuels)
- Auto-complétion de l'entrée (saisie Départ/Arrivée)
  - suggestions en liste déroulante
  - clic simple pour sélectionner
  - `TAB` valide la meilleure suggestion
- Recherche `Entrée` (touche `Return`) active la recherche
- Filtre ligne facultatif (E, A, C1, C2, B, ...)
- Résultats affichés dans un tableau à colonnes : `LIGNE`, `Direction`, `Départ`, `Arrivée`, `Durée`, `Type`
- Affichage du terminus du trajet (direction logique : headsign ou partie route)
- `+1h` : recharge le plan pour l'heure suivante, indication textuelle
- Liste arrêts par ligne en pop-up

## Prérequis

- Python 3.8+ (testé 3.12)
- Paquets Python
  - `requests`
  - (inclus dans standard lib : `tkinter`)


## Installation

```bash
cd "c:\Users\jerom\Desktop\tag express website project"
python -m pip install requests
```

## Exécution

```bash
python tkinter_tag.py
```

## Utilisation

1. Saisir arrêt de départ (ex : `Pont de Vence`).
2. Saisir arrêt d'arrivée (ex : `Alsace Lorraine`).
3. Optionnel : saisir ligne (ex : `E`), sinon toutes les correspondances sont considérées.
4. Cliquer sur `Rechercher` ou `Enter`.
5. Brancher sur `+1h` pour explorer suivants départs.
6. `Lister arrêts` permet d'afficher le cluster d'une ligne.

## Personnalisation

- Ajouter / modifier dans `stops_dict` pour points non présents en API.
- Éventuellement ajouter `line_names` pour liaisons spécifiques.

## FAQ

- *Pas d'itinéraire trouvé ?* Vérifier l'orthographe exact des arrêts.
- *Problème API 204 ?* l'app utilise les clusters pour trouver les arrêts connus.
- *Problème interface* : vérifier que `tkinter` est installé (sous Windows inclus).

## Bugs

- Si vous constatez le moindre bug, n'hésitez pas à me le faire savoir dans `Issues`
