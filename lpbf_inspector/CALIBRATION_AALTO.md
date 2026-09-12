# Ancien essai de calibration spatiale Aalto

**Archive expérimentale, retirée du parcours de l'interface.** Le logiciel
analyse désormais chaque job sur ses propres images, avec une calibration
initiale de gris indépendante. Les profils et résultats décrits ci-dessous
ne sont pas utilisés par ce mode. Voir [README.md](README.md).

Les images originales ne contiennent pas les rectangles affichés par l'ancienne
galerie. Les JPEG et les XML sont séparés ; aucune suppression de pixels ni
retouche des originaux n'est effectuée.

## Une bibliothèque par fabrication

| Date | Identifiant source | Photos | Photos avec rectangles exploitables | Rectangles |
|---|---|---:|---:|---:|
| 01/12/2021 | SI383820211201123521 | 1 000 | 406 | 572 |
| 26/02/2024 | SI383820240226095904 | 271 | 127 | 467 |
| 18/03/2024 | SI383820240318120348 | 1 367 | 996 | 3 961 |

Total : 2 638 photos, 1 529 photos avec 5 000 rectangles exploitables.
Un autre XML contient un rectangle de surface nulle. Les 1 109 photos sans
rectangle exploitable restent analysées mais ne sont pas classées saines.

## Séparation entre inférence et évaluation

`aalto_detector.detect_image(path, profile)` n'accepte qu'une photo et un
profil numérique. Il ne lit ni XML ni provenance ni résultat d'évaluation.
Il est également utilisable indépendamment de la galerie :

```powershell
python aalto_detector.py photo_brute.jpg --profile aalto_runs/profile_SI383820211201123521.json --output indications.json
```

Ce profil correspond à la caméra et au cadrage Aalto ; son transfert sur
une autre machine demanderait une nouvelle calibration et évaluation.

Le cache de candidats est calculé à partir des seules images. Le navigateur
reçoit les prédictions et les métriques agrégées, jamais les rectangles des
auteurs. Les annotations sont conservées intactes dans les données source.

`aalto_calibration.run_calibration` choisit les seuils sur deux jobs et
évalue le troisième ; le procédé est répété trois fois. Les photos voisines
d'une même fabrication ne passent pas d'un côté à l'autre de cette séparation.
Les trois profils ont des paramètres éventuellement différents. Le fichier
`aalto_runs/results.json` contient les prédictions obtenues hors job ; aucun
profil recalibré sur ses propres annotations ne les remplace après l'évaluation.

Il s'agit d'une évaluation interne rétrospective : seul le choix des seuils
est tenu à l'écart du job évalué. La conception des filtres a bénéficié de
l'examen de quelques images de la collection. Ce n'est pas une validation
externe indépendante ou une garantie de transfert industriel.

## Détecteur et calibration

- Images réduites à 640 × 512 pour le calcul ; coordonnées de sortie ramenées
  dans les pixels originaux. Le gros plan utilise toujours la photo originale.
- Masque polygonal du lit pour cette caméra, défini visuellement hors châssis,
  indépendant des annotations. Pas de masque dérivé des rectangles à détecter.
- Résidu par rapport à un fond lissé, recherche de contrastes locaux et de
  stries horizontales fines par intégration directionnelle, morphologie et composantes connexes. Pas de CNN.
- Contrastes sombres : seuils 4, 7, 11, 17, 25 et surfaces minimales 16 ou
  40 pixels réduits. Stries : seuils indépendants 0,6, 1,0, 1,5 ou 2,5 ;
  recherche possible seule ou combinée aux contrastes sombres : 54 réglages. Maximisation du F1 à IoU ≥ 0,30
  sur les images annotées des deux jobs de calibration.
- La sélection et la suppression des cadres redondants dépendent des seuls
  pixels, scores et paramètres ; aucune annotation ne guide le cadrage.
- Cache SQLite versionné avec empreinte source, contrôle SHA-256 lors de
  l'extraction, deux images en calcul simultanément. Cache destiné à ce jeu
  de démonstration, pas au stockage en mémoire d'un job de plusieurs To.

Méthodes : [morphologie OpenCV](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html),
[composantes connexes OpenCV](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html).

## Mesures à interpréter

Un rectangle prédit peut correspondre à au plus un rectangle source et
inversement. L'appariement suit les scores décroissants, avec intersection
sur union (IoU) ≥ 0,30 ; le bilan à IoU ≥ 0,50 est aussi publié.

- Rappel : rectangles source retrouvés / rectangles source disponibles.
- Correspondance (champ `precision`) : prédictions appariées / prédictions
  sur les photos annotées.
- Manqués : rectangles source sans prédiction appariée.
- Sans correspondance : prédictions non appariées sur les photos annotées.
  Ce ne sont pas nécessairement de faux défauts, les labels pouvant être incomplets.
- Charge de revue : nombre total d'indications et de photos signalées sur
  tout le job, y compris celles sans annotation exploitable.

Aucune spécificité ni exactitude globale n'est calculée en présumant les
photos non annotées négatives. La définition des annotations est une zone
visuelle, pas une mesure de défaut interne. Les compteurs restent des
acquisitions ; la correspondance avec les étapes et hauteurs est inconnue.

L'interface fournit les mesures de chaque job et leur export JSON. Les
résultats numériques de l'exécution sont conservés dans `aalto_runs/results.json`.
Source des images et XML : [Aalto, Yin et al., 2025, CC BY 4.0](https://zenodo.org/records/14996806).


## Résultats mesurés le 9 septembre 2026

Les 2 638 photos ont été calculées. Les variantes de stries fines ont été
comparées mais n’ont pas été retenues par la calibration hors job.

| Job | Retrouvés / annotations | Rappel IoU ≥ 0,30 | Correspondance IoU ≥ 0,30 | Rappel IoU ≥ 0,50 | Alertes sur toutes les photos |
|---|---:|---:|---:|---:|---:|
| SI383820211201123521 | 112 / 572 | 19.6% | 6.1% | 11.0% | 2172 |
| SI383820240226095904 | 110 / 467 | 23.6% | 4.2% | 16.9% | 6549 |
| SI383820240318120348 | 44 / 3961 | 1.1% | 0.8% | 0.4% | 5693 |

**Conclusion : performances insuffisantes pour une revue fiable ou un
contrôle de production.** Au total, 266 rectangles sur 5 000 sont retrouvés
à IoU ≥ 0,30, et de nombreuses alertes ne correspondent pas aux annotations.
Le fonctionnement sans aide à l’inférence est vérifié ; une simple calibration
de ces seuils ne suffit pas pour retrouver les indications des chercheurs.

Le premier traitement de la version 1 a demandé 701,53 secondes, extraction
et évaluation comprises. La reprise finale de la version 2 depuis le cache
complet a pris 129,24 secondes pour la lecture, la calibration et la publication des
résultats. Ces durées ne représentent pas un chronométrage d’une exécution
complète de la version finale depuis un cache vide. Le cache SQLite des
candidats occupe environ 107 Mo.

32 tests Python, les tests du rendu JavaScript et la vérification HTTP des
2 638 identifiants dans trois bibliothèques séparées contrôlent le
fonctionnement. Une inférence indépendante depuis le JPEG et le profil a
été comparée aux résultats affichés pour une photo de chaque job. Les
résultats fonctionnels et les performances de détection sont deux constats
distincts. Voir `research/verification_aalto_v2.json`.
