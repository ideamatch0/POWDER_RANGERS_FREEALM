# Images publiques de lit de poudre LPBF

Recherche et vérification des archives : 8 septembre 2026.

## Choix pour les premiers essais

Le jeu **NIST AMMT — Overhang Part X4** est le meilleur point de départ
pour vérifier la comparaison temporelle : étapes et numéros de couches
sont documentés. Le jeu **Aalto / EOS M290** est un complément proche
des JPEG d'une machine industrielle, avec des annotations exploitables
pour une évaluation manuelle sans entraîner de modèle.

| Jeu | Contenu pertinent | Téléchargement | Usage proposé |
|---|---|---|---|
| [NIST AMMT — Overhang Part X4](https://doi.org/10.18434/M32233) | 1 500 PNG de caméra de couche ; deux étapes, trois éclairages ; 250 images par série | Archive `LayerCamera_PNGs.zip` : 8,27 Go | Vérifier ordre des couches, séparation des étapes, indicateurs temporels et effets d'éclairage |
| [Aalto — Annotated Image Dataset for defects detection in LPBF](https://zenodo.org/records/14996806) | 2 638 JPEG de lit de poudre EOS M290, 1 280 × 1 024 ; photos avant/après exposition ; annotations disponibles pour une partie des images | `Original Images and Manual Labels.zip` : 437,5 Mo, incluant aussi les images OT | Tester le rendu des JPEG industriels, examiner des indications annotées ; correspondance compteur/couche/étape à confirmer |
| [ORNL — Peregrine v2021-03](https://doi.ccs.ornl.gov/dataset/e2decf63-021c-563c-8729-ffe02769176c) | 20 couches par technologie, dont LPBF ; images calibrées et étiquettes par pixel | Accès indiqué via Globus ; fichiers non téléchargés ici | Compléter les exemples de défauts ; continuité temporelle non établie pour notre usage |

## Vérifications effectuées sur les fichiers

Les sommaires ZIP ont été lus directement par requêtes HTTP partielles,
sans télécharger intégralement les archives.

Pour le NIST, les six séries sont :

- `A0002a.PNG` à `A0251a.PNG`, et idem pour les éclairages b et c : après étalement.
- `B0001a.PNG` à `B0250a.PNG`, et idem pour les éclairages b et c : après fusion.

Il faut donc conserver les numéros d'origine : les débuts et fins des
deux étapes sont décalés. Une seule caméra de couche est employée avec
trois éclairages ; ces éclairages ne constituent pas trois caméras.
Dans le prototype, le champ de canal `a` représente l'éclairage a.

Le premier échantillon local comprend **20 PNG**, couches **120 à 129**, étapes A
et B, éclairage a. Il pèse **113 663 029 octets**, soit environ 113,7 Mo.
Les fichiers sont en niveaux de gris **16 bits, 2 000 × 2 000 pixels**.
Leur échelle numérique observée va de 0 à 65 535. Des zones sont saturées ;
la mesure y est limitée et une analyse de l'image complète peut produire
des indications hors des pièces. Un aperçu comparatif est fourni dans
`research/nist_comparaison_couche125.jpg`.

La démonstration utilise désormais une série élargie de **200 PNG**, couches
**80 à 179**, dans `datasets/nist_80_179` : 100 images après étalement et
100 après fusion, toujours avec l'éclairage a. Elle représente environ
**1,135 Go**. Les 20 images initiales sont incluses et le premier dossier
est conservé. Le script `research/fetch_nist_series.py` extrait uniquement
les entrées nécessaires de l'archive, vérifie leur taille et CRC, puis
enregistre les empreintes SHA-256 dans le nouveau `provenance.json`.
La série n'est proposée par l'interface qu'après achèvement du téléchargement.

Pour Aalto, le sommaire contient **2 638 JPEG PB**, **2 674 JPEG OT**,
**1 530 fichiers d'annotations XML PB** et **1 124 fichiers XML OT**.
Les compteurs et horodatages sont présents dans les noms PB, par exemple :

`SI383820211201123521_00009_20211201T125928.564000.jpg`

La présence de compteurs ne suffit pas à attribuer automatiquement le
numéro de couche : il reste à établir l'alternance exacte des étapes et
les éventuels trous. Les images OT ne doivent pas être mélangées aux
photos PB pour l'analyse prévue.

Mise à jour du 9 septembre 2026 : l'archive Aalto originale a été
téléchargée intégralement. Son MD5 correspond à celui publié par Zenodo :
`9d5ed884aecacb9ada5d0cca7c15d4b7`. Les 2 638 PB et leurs XML sont installés
dans `datasets/aalto_pb`. Les trois jobs contiennent respectivement 1 000,
271 et 1 367 photos. 1 529 images ont des rectangles exploitables ; le nombre
de fichiers XML reste 1 530. Un rectangle de surface nulle a été identifié
dans les annotations originales et n'est pas affiché. Les coordonnées
originales sont conservées dans la provenance et les XML d'origine.

La version actuelle propose trois bibliothèques Aalto, une par job, et
utilise exclusivement les pixels de chaque job. La calibration du niveau
de gris et l'historique des changements sont propres à cette fabrication.
Les annotations ne sont ni affichées ni utilisées dans ce mode. L'ancien
protocole croisé reste archivé dans `CALIBRATION_AALTO.md`.
Le numéro affiché est un compteur d'acquisition, pas une couche supposée.
L'analyse temporelle suit ces acquisitions avec un intervalle explicite de
1 ou 2. La correspondance étape/couche n'est pas qualifiée : aucune hauteur
Z ni étiquette fusion/étalement n'est déduite automatiquement.

## Autres séries de photos recherchées le 9 septembre 2026

### NIST — Three-Dimensional Scan Strategies

Il s'agit d'un **autre job** que les séries Overhang Part X4 déjà installées.
Dix pièces rectangulaires en IN625 ont été fabriquées avec différentes
stratégies de balayage. Le jeu comprend des images du lit avant et après
étalement. Les fichiers de la caméra de couche doivent être utilisés, plutôt
que les figures explicatives annotées des articles ou les images du bain.
Source : [catalogue officiel NIST](https://www.nist.gov/el/ammt/datasets),
[données et téléchargement](https://doi.org/10.18434/M32044),
[description des fichiers](https://nvlpubs.nist.gov/nistpubs/jres/124/jres.124.033.pdf).
Les BMP LayerCamera nécessitent une conversion sans perte en PNG avant
l'import actuel. Jeu non téléchargé lors de cette mise à jour.

### ORNL — 64 cylindres, publication du 21 avril 2025

Une fabrication en acier 316H sur Concept Laser M2 Series 5 comporte
64 cylindres, avec des images visibles avant et après étalement à chaque
couche, ainsi que des données thermiques, tomographiques et de fatigue.
Les données sont distribuées en HDF5 via Globus. Source primaire :
[notice et accès ORNL](https://doi.ccs.ornl.gov/dataset/bc373c52-5cdd-50cd-bb81-dcc85799fe35),
[DOI 10.13139/ORNLNCCS/2524534](https://doi.org/10.13139/ORNLNCCS/2524534).

Cette série semble particulièrement adaptée aux deux étapes recherchées.
L'accès au contenu HDF5 et les pixels n'ont pas été vérifiés localement :
extraire uniquement les canaux de photos, vérifier leur échelle et leur
correspondance aux couches avant import. Les masques ou résultats d'analyse
éventuellement présents dans le conteneur doivent rester séparés des images.
L'import HDF5 direct n'est pas encore développé. Les conditions de
réutilisation doivent être consultées dans la distribution officielle.

## Paramètres propres à chaque jeu

- **Votre machine : 60 µm**, valeur enregistrée dans `config.example.json`.
- **NIST X4 : 20 µm**, valeur indépendante dans `config.nist_sample.json`.
- **Aalto : 20 ou 40 µm selon le lot**, selon la description publiée.

Ces différences n'empêchent pas les premiers essais d'algorithme, mais
les seuils, fenêtres temporelles et performances ne seront pas directement
transférables à votre machine. La hauteur se calcule depuis le véritable
numéro de couche, une origine Z et l'épaisseur ; l'épaisseur seule ne
permet pas de retrouver un numéro de couche depuis une photo.

## Provenance et réutilisation

- NIST : Brandon Lane, *Process Monitoring Dataset from the Additive
  Manufacturing Metrology Testbed (AMMT): Overhang Part X4*, 2020,
  [DOI 10.18434/M32233](https://doi.org/10.18434/M32233).
  [Description scientifique complète](https://pmc.ncbi.nlm.nih.gov/articles/PMC10871811/).
  [Notice d'accès et licence NIST](https://www.nist.gov/open/license).
- Aalto : Xinyi Yin, Jan Sher Akmal, Mika Salmi, Roy Björkstrand,
  *Annotated Image Dataset for defects detection in Laser Powder Bed
  Fusion*, 2025, [DOI 10.5281/zenodo.14996806](https://doi.org/10.5281/zenodo.14996806).
  Licence **CC BY 4.0**, vérifiée dans la
  [notice JSON Zenodo](https://zenodo.org/api/records/14996806), dont une
  copie figure dans `research/zenodo_metadata.json`.
- ORNL : Luke Scime et collaborateurs, *Peregrine v2021-03*, 2021,
  [DOI 10.13139/ORNLNCCS/1779073](https://doi.org/10.13139/ORNLNCCS/1779073).
  L'accès effectif via Globus et les modalités de réutilisation ne sont
  pas vérifiés ici.

Les noms d'origine, les chemins dans l'archive et les empreintes SHA-256
de l'échantillon NIST sont conservés dans
`datasets/nist_sample/provenance.json`. Les CRC des entrées ZIP ont été
vérifiés à la lecture. L'empreinte SHA-256 de l'archive complète n'a pas
été vérifiée, puisque seuls certains fichiers ont été téléchargés.

Pour récupérer de nouveau la série de démonstration :

```powershell
python research/fetch_nist_series.py --first 80 --last 179
```

L'empilement 3D garde les numéros de couches et hauteurs NIST (1,600 à
3,580 mm pour cette série). Il est séparé par étape et utilise des aperçus
réduits. L'absence de calibration X/Y empêche de présenter ce volume comme
une reconstruction métrique de la pièce.

## Premier résultat exploratoire

Les 20 images NIST ont été décodées et mesurées avec une échelle fixe,
sans conversion 16 bits qui saturerait tous les pixels au-dessus de 255.
Chaque étape a cinq images d'initialisation et cinq images évaluées.
Le premier réglage sur l'image entière produit 163 indications regroupées.
Ce nombre ne mesure pas des défauts : les zones extérieures aux pièces,
les objets en mouvement, la saturation et les changements normaux doivent
encore être étudiés. Aucune indication NIST n'a été validée ici comme défaut.

La prochaine expérience utile consiste à définir des régions d'intérêt,
choisir des séquences normales et atypiques, puis mesurer le nombre
d'indications à examiner et les indications manquées. Les annotations
Aalto pourront aider à cette évaluation sans apprentissage automatique.

## Passage sur la série de 200 photos

Le 8 septembre 2026, les 200 photos ont été mesurées sans erreur en
30,14 secondes sur le poste de démonstration, avec les derniers réglages
utilisateur : image entière, zones de 64 × 64 pixels, seuil de changement
40/255. Les deux étapes ont chacune 5 images d'initialisation et 95 images
évaluées. Le résultat comporte 182 indications à examiner, sans qualification
comme défauts. Les 200 aperçus 3D ont également été décodés via le serveur
local, ainsi que des comparaisons avant/pendant/après aux trois cadrages.
Le résultat de cette vérification figure dans `research/verification_200.json`.

## Deux jobs supplémentaires importés le 9 septembre 2026

| Bibliothèque | Extrait installé | Images | Échelle |
|---|---|---:|---|
| NIST · Three-Dimensional Scan Strategies | Couches 2–101 | 200 | 20 µm, 2000 × 2000, gris 8 bits |
| ORNL · M2 AMMTO Fatigue Blanks 05 | Couches 70–169 | 200 | 100 µm, 2844 × 2844, gris 8 bits |

Chaque extrait représente un seul job, avec une photo après étalement et
une après fusion pour chaque couche. Les deux bibliothèques occupent
1 260 108 915 octets de PNG, soit environ 1,26 Go. Les archives entières ne
sont pas téléchargées. Les sources et empreintes de chaque fichier sont
conservées dans les `provenance.json` de leurs dossiers.

**NIST** : [jeu officiel, DOI 10.18434/M32044](https://doi.org/10.18434/M32044),
[publication décrivant les acquisitions](https://nvlpubs.nist.gov/nistpubs/jres/124/jres.124.033.pdf).
Le script `research/fetch_nist_scan.py` extrait les entrées LayerCamera de
l'archive ZIP64 par lectures HTTP partielles. A = après étalement, B = après
fusion. Les BMP originaux sont convertis sans perte en PNG : CRC des entrées,
égalité des pixels décodés et empreintes SHA-256 sont vérifiés. Ce sont les
photos du capteur, sans les annotations des figures de la publication.

**ORNL** : [notice officielle, DOI 10.13139/ORNLNCCS/2524534](https://doi.ccs.ornl.gov/dataset/bc373c52-5cdd-50cd-bb81-dcc85799fe35),
[miroir public utilisé](https://huggingface.co/datasets/ppak10/ORNL-LPBF-Cylinders).
Le conteneur HDF5 de 127 808 960 296 octets est lu par blocs, sur une révision
figée du miroir. `research/fetch_ornl_cylinders.py` extrait uniquement
`slices/camera_data/visible/0` (après fusion) et `visible/1` (après étalement).
Aucun canal de segmentation ni d'annotation n'est chargé. Les producteurs
ont déjà corrigé l'éclairage, la distorsion et la perspective : il s'agit
d'images prétraitées sans annotations, pas du RAW natif de la caméra.
Le README du jeu indique aucune restriction de réutilisation ; ce constat
n'est pas une attribution de licence SPDX. Copies de la notice et des
méthodes : `research/ornl_readme.txt` et `research/ornl_methods.docx`.

L'index HDF5 commence à 0. La hauteur affichée est relative : indice × 0,1 mm,
soit 7,0 à 16,9 mm pour cet extrait. Le script conserve un seul bloc de 35
couches dans un fichier temporaire et vérifie les pixels après conversion.
Des comparaisons supplémentaires avec le lecteur HDF5 source, comprenant
un bloc non compressé et les bords d'image, figurent dans
`research/ornl_pixels_verified.json`. L'empreinte du HDF5 entier n'est pas
vérifiée : seuls les blocs nécessaires ont été récupérés.

Ces deux jobs suivent le même moteur, la même revue et le même empilement
que les bibliothèques existantes. Les règles ne sont pas calibrées sur un
autre job ni sur les annotations. Aalto utilise un axe d'acquisition en 3D,
car sa correspondance aux couches physiques n'est pas établie.
