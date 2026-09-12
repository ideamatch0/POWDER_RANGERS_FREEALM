# Powder Ranger — Every layer under watch.

## Version 0.3.1 — English desktop edition

The application interface, single-job review and new report builder are in English.
The Windows executable includes Python, NumPy, Pillow and the local web interface.
See [Windows quick start and installation](WINDOWS_QUICK_START.md) for the current user guide.
Build with `python build_windows.py`; run from source with `python desktop_launcher.py`.

Reports offer **Summary**, **Detailed review** and **Presentation** templates, editable
job details, background generation with progress/cancellation, and offline HTML download.
Embedded oblique and top views show retained indications over cyan photographic part
sections when identified post-melting images are available. Unknown-stage acquisitions
use a photographic stack. Reports capture the current decision revision and persistence
filter, including only retained indications. The browser print dialog supports PDF export.

The Windows package starts with an empty library; public datasets and existing decisions
are not bundled. Application data lives in `%LOCALAPPDATA%\PowderRanger`, separately
from the installed executable. Source photographs remain in their imported folders.

Validation: `python -m unittest discover -s tests -q`, the review/stack/report tests in
`tests/*.cjs`, and the packaged launcher's `--self-test` with an isolated `--data-dir`.

The French notes below document the original prototype and research work.

Ce prototype Python matérialise le cadrage de la première version :
détection de changements dans un job, après fabrication, sans apprentissage.
Il sert à expérimenter sur des images publiques avant adaptation aux
fichiers de votre machine. Il ne constitue pas un logiciel de contrôle
validé sur votre production.

Les données publiques et leur provenance sont décrites dans
[DONNEES_PUBLIQUES.md](DONNEES_PUBLIQUES.md). Le cadrage est dans
[ARCHITECTURE.md](ARCHITECTURE.md).

## Essayer dans le navigateur

Une interface locale sombre permet d'essayer le moteur Python sur
les **200 photos publiques NIST**, soit 100 couches consécutives (80 à 179),
avec une photo après étalement et une après fusion par couche :

```powershell
python local_app.py
```

Ouvrir [Powder Ranger](http://127.0.0.1:8765/) sur le même ordinateur.
L'accueil présente le grand écusson Powder Ranger, le slogan anglais et deux
cartes de mode. Le balayage lumineux se répète toutes les six secondes ; le
bouton **Pause / Reprendre** contrôle l'animation. La préférence système de
réduction des animations est respectée par défaut et les boucles sont suspendues
quand l'onglet est masqué. Aucun calcul d'analyse n'est lancé depuis l'accueil.
L'espace de travail reste accessible directement à
[la page d'analyse](http://127.0.0.1:8765/workspace). Le logo et le lien **Accueil**
permettent de revenir au choix des modes. La carte comparaison ouvre sa
présentation à `/workspace?mode=reference`, avec son statut « À venir ».
Choisir **Analyse d’un job seul**, puis une bibliothèque. Le mode
**Comparaison entre un job et son job de référence** est présenté en amont,
mais reste à développer ; il ne lance aucun calcul.
Le sélecteur « Bibliothèque active » donne accès aux séries NIST, aux
trois bibliothèques Aalto/EOS M290 (une par job), au job ORNL et aux dossiers ajoutés par l'utilisateur.
Deux extraits supplémentaires sont installés : **NIST 3D Scan Strategies**
(couches 2–101, 200 photos) et **ORNL 64 cylindres** (couches 70–169, 200 photos).
Les images ORNL sont sans annotations, mais corrigées par leurs producteurs
pour l'éclairage et la perspective. Leurs provenances indiquent le miroir public utilisé.
La page permet de lancer le calcul, modifier le seuil et la taille des
zones, limiter l'analyse à un rectangle approximatif autour des quatre
pièces, sélectionner l'étalement seul, la fusion seule ou les deux, comparer
les images et enregistrer les décisions. Les deux étapes ont toujours des
historiques indépendants. Une analyse d'une seule étape mesure 100 photos.
Les résultats
des nouveaux réglages sont conservés dans `web_runs/`. Relancer les mêmes
réglages sur la même série retrouve leur projet et les décisions précédemment
enregistrées. L'empreinte de l'inventaire distingue les séries ; les anciens
essais sur 20 images restent conservés dans leurs dossiers. Les réglages du
navigateur sont mémorisés par bibliothèque dans `web_settings.json`.

La revue affiche une petite vue d'ensemble avec le cadre rouge et trois
**gros plans au même cadrage** : avant, couche signalée et après. Le menu
« Contexte autour » règle la marge (resserré, standard ou large). Les images
sont recadrées avant réduction, avec une échelle de gris fixe. Les cadres
bleus avant/après repèrent la même position ; ils ne sont pas des détections
sur ces couches. Une image absente ou de dimensions différentes est signalée.
Changer le cadrage conserve le commentaire en cours de saisie.

**Retenir** et **Écarter** enregistrent la décision puis ouvrent automatiquement
l'indication suivante dans l'ordre de la liste et des filtres actifs, y compris
au passage d'une page à l'autre. « Laisser à examiner » reste sur l'indication.
La fin de liste est signalée ; une erreur de sauvegarde empêche d'avancer.

Chaque indication porte un **score de priorité de 0 à 100**, identique dans
la liste, sa fiche, l'empilement et le rapport. Il combine l'intensité relative
au seuil de détection et la persistance : `100 × √(V × P)`, avec
`V = r / (r + 2)` et `P = n / (n + 3)`. `r` est le dépassement du seuil au pic ;
`n` le nombre d'images comparables consécutives. Ainsi `r=2, n=3` donne 50/100
et `r=6, n=6` donne 70,7/100. Ces constantes sont des choix de priorisation
exploratoires, pas un étalonnage sur des défauts qualifiés. Le détail des deux
composantes et la formule restent consultables. Le score dépend des réglages
du job ; il ne représente ni une probabilité ni une gravité matière.

**Ordre de revue** choisit la chronologie ou le score décroissant. À score
égal, la chronologie départage les indications, puis leur identifiant stable.
Le passage automatique après Retenir/Écarter respecte cet ordre et les filtres,
y compris si la décision retire l'indication de la liste. Le choix est mémorisé
dans ce navigateur. Le calcul temporel des mesures continue toujours dans
l'ordre des couches, indépendamment du tri de la revue. Aucun recalcul de
l'analyse et aucune nouvelle calibration ne sont requis pour les scores.

Le champ **Persistance minimale** filtre immédiatement les résultats sans
relancer l'analyse : **1** affiche tout ; **3** exige au moins trois couches
consécutives avec une indication de même catégorie, même caméra et même étape,
dans des zones qui se recouvrent d'une image à la suivante. Une couche absente
ou sans indication coupe la chaîne. Plusieurs rectangles sur une seule photo
ne comptent jamais comme plusieurs couches. Sur Aalto, on compte les acquisitions
comparables selon l'intervalle choisi (1 ou 2), et non une hauteur physique.

Ce réglage, mémorisé par bibliothèque, s'applique à la liste, aux repères 3D et
au rapport des indications retenues. Les détections et décisions masquées restent
conservées : revenir à 1 les retrouve. Le bilan de calcul affiche explicitement
les nombres avant ce filtre. Le rapport indique le minimum utilisé. Il s'agit
d'une persistance de détection optique, pas d'un critère de conformité matière.

L'onglet **Empilement 3D des couches** affiche les photographies d'une seule
étape et caméra à la fois. Les indications sont colorées selon leur score de
priorité, du jaune au rouge en cinq tranches de 20 points, avec légende.
La case « Couleurs selon le score » permet de retrouver des repères tous rouges.
Les repères restent au plan du pic, avec un point visible pour les petites zones.
Elles restent visibles à travers les photos ; cliquer sur un point ouvre
sa revue 2D. Les filtres proposent les indications à examiner et retenues,
les retenues seules ou celles de la couche de coupe. Les indications
écartées sont exclues de cette représentation. Le rectangle au pic n'est
pas extrapolé sur toutes les couches couvertes par l'événement.
Faire glisser pour pivoter, utiliser la molette pour zoomer
et déplacer la coupe pour explorer les couches. Les touches fléchées et
plus/moins contrôlent aussi la vue. Le cadrage, l'opacité des couches
inférieures et la densité de plans sont réglables. Les aperçus 3D sont
limités à 384 pixels. Environ 128 plans répartis dans le volume sont chargés
par trois lecteurs, plus le chargement de la coupe courante à la demande.
Le cache graphique est limité à 160 textures ; tous les repères restent affichables.
WebGL est nécessaire ; aucune bibliothèque 3D ni connexion externe n'est
chargée. La vue propose des photographies et, après fusion, des sections
segmentées approximatives ; elle ne produit pas de surface CAO ou STL. Z utilise les hauteurs réelles
NIST et la convention relative ORNL, mais son affichage est amplifié ; X/Y
restent en pixels non calibrés. **Aalto dispose de la même 3D et de la même
revue**, avec un axe vertical en numéros d'acquisition : aucune hauteur
physique ni étape fusion/étalement n'est inventée.

Après fusion, le menu **Représentation → Forme extraite · cyan** retire le fond
photographique et empile les sections extraites en cyan. **Photos + forme**
superpose les deux. Le contrôle **Contraste minimal** règle la sélection :
plus bas, davantage de zones sont extraites. Le masque cyan est superposé à
la photo de coupe, avec la proportion extraite et une alerte si elle est nulle
ou très étendue. Les indications colorées sont dessinées après les sections
pour rester visibles, et les scores les plus élevés en dernier.

L'extraction utilise uniquement le contraste local de chaque photo après fusion,
avec un seuil robuste au fond, un nettoyage des petits îlots et le comblement
de petits interstices fermés. Aucun label de chercheur, job de référence ou
maillage CAO n'est lu. Le masque est calculé sur l'image entière puis recadré,
avec la même normalisation fixe 8/16 bits que les mesures. Les reflets, les
ombres et les sections peu contrastées peuvent donner des formes incomplètes
ou parasites ; certaines petites cavités peuvent être comblées. Il faut
vérifier la superposition sur les photographies. Ce n'est pas une reconstruction
métrologique ni une détection de porosités internes.

Le calcul des sections se fait à la demande, avec progression et temps restant
estimé. Il travaille à 512 px maximum et charge environ 128 sections réparties
dans le volume, plus la coupe choisie. Deux lecteurs traitent l'aperçu et un
chargement supplémentaire au maximum traite la coupe courante. Les caches de
masques PNG et textures RGBA sont bornés à 160 entrées ; changer d'étape, de job
ou de contraste annule les chargements devenus inutiles. Ce réglage ne change
ni l'analyse ni les décisions. La forme après fusion est indisponible sur les
acquisitions Aalto dont l'étape physique reste inconnue ; leurs photographies,
indications et scores restent explorables en 3D.

Le bouton d'export télécharge un rapport HTML des indications retenues,
avec la vue d'ensemble et les trois gros plans intégrés (marge standard).
Il est disponible après l'analyse et au moins
une indication retenue ; cet export de démonstration est limité à 500
indications retenues, avec refus explicite au-delà. Le rapport peut être
imprimé depuis le navigateur.

Cette interface utilise réellement le moteur de calcul. L'import local
référence les fichiers de production sans les copier ni les envoyer sur
Internet. L'inventaire et son tri utilisent SQLite pour borner la mémoire.
Le serveur écoute uniquement sur `127.0.0.1`, et le lien n'est pas un site
hébergé accessible depuis un autre ordinateur. Il reste utilisable tant
que le processus Python est actif.

## Importer ou explorer une autre bibliothèque

« Importer un dossier… » ouvre le formulaire de nom, chemin, épaisseur,
origine Z, échelle 8/16 bits et lecture des noms de fichiers. « Parcourir… »
utilise le sélecteur de dossiers Windows si Tk est disponible ; le chemin
peut aussi être collé directement. Les sous-dossiers sont parcourus. Les
groupes `camera`, `layer` et `phase` et les alias sont configurables.
Un dossier doit représenter un seul job ; les doublons d'identifiants sont
refusés et les images non reconnues sont comptées. L'indexation apparaît
dans la barre d'avancement et peut être interrompue. Après l'ajout, lancer
l'analyse avec l'étape et les réglages souhaités. Le catalogue est conservé
dans `libraries.json`, séparément des originaux.

Les **trois bibliothèques Aalto / EOS M290** correspondent chacune à une
fabrication : 01/12/2021 (1 000 photos), 26/02/2024 (271 photos),
18/03/2024 (1 367 photos). Aucun mélange de leurs images ou décisions.
Les photos sont brutes. **Les annotations des auteurs et les autres jobs
ne sont utilisés ni pour la calibration du gris, ni pour la détection.**
Le bouton **Calibrer le niveau de gris** mesure la moyenne des 20 premières
acquisitions du job et l'enregistre. Le bouton distinct **Analyser ce job**
prépare cette calibration si nécessaire, puis traite toutes ses images.
Aucun complément OpenCV n'est nécessaire pour ce parcours.

L'analyse compare des zones à leur historique médian récent, suit leur
texture et leurs dérives, et surveille la luminosité globale. La moyenne
de gris de chaque image est calculée sur les pixels du cadrage choisi.
Le seuil et la taille des zones restent réglables. Un cadrage du lit permet
d'exclure une partie du châssis ; il n'est pas une segmentation des pièces.

Les résultats et mesures réutilisables sont dans `job_runs/<bibliothèque>/`.
Une interruption conserve les mesures ; une relance reconstruit l'historique
en les réutilisant. Les décisions, isolées par job et empreinte d'analyse,
restent dans `aalto_runs/review.sqlite`. Les modifications d'annotations
ou d'un autre job n'invalident pas l'analyse du job sélectionné.

Les compteurs d'acquisition sont ordonnés, mais ne sont pas assimilés à
des couches. L'intervalle **1** compare les acquisitions consécutives ;
l'intervalle **2** crée deux historiques indépendants, pairs et impairs,
pour une alternance à confirmer visuellement. Il n'attribue pas les noms
fusion/étalement. Après un trou ou une image illisible, l'historique concerné
est réinitialisé. Les photos d'initialisation sont comptées séparément.
Les gros plans avant/après montrent la même zone au même intervalle.

Le bilan compte les images évaluées, les indications et les erreurs ; il
ne présente pas une mesure de fiabilité contre les annotations. Une
modification normale de géométrie peut être signalée ; un défaut stable
depuis le début peut rester invisible à cette méthode temporelle. Les
étapes et hauteurs restent à documenter avant une 3D Aalto à hauteur physique.

L'ancien essai spatial de calibration sur deux autres jobs est conservé
pour traçabilité dans `aalto_calibration.py` et [CALIBRATION_AALTO.md](CALIBRATION_AALTO.md).
Il n'est plus appelé par l'interface et ne fournit plus ses résultats.

Deux autres sources de photos de lit, NIST Three-Dimensional Scan Strategies
et ORNL 2025 (64 cylindres), sont accessibles via les liens proposés dans
l'interface et documentées dans [DONNEES_PUBLIQUES.md](DONNEES_PUBLIQUES.md).
Elles ne sont pas encore téléchargées. L'import local accepte JPEG/PNG ;
une extraction des canaux image HDF5 ou conversion BMP vers PNG est nécessaire.

L'étude des offres industrielles et les fonctions proposées sont dans
[ANALYSE_MARCHE_2026-09-09.md](ANALYSE_MARCHE_2026-09-09.md).

## Fonctions présentes

- Indexation des chemins sur disque, tri numérique par couche, séries
  indépendantes par caméra/canal et par étape.
- JPEG 8 bits et PNG 8/16 bits ; échelle fixe explicite pour le 16 bits.
- Statistiques par blocs utilisant les pixels d'origine : moyenne,
  dispersion, minimum et maximum. ROI rectangulaire configurable par canal.
- Changements locaux brusques comparés à un historique médian robuste,
  suivi de dérives locales et globales par moyenne pondérée.
- Regroupement spatial et prolongement simple sur couches consécutives.
- Cache SQLite des mesures compressées, avancement et estimation du temps
  restant dans le terminal. Interruption par Ctrl+C, puis reprise avec la
  même commande et les mêmes paramètres.
- Pages HTML locales de revue : vue repère et gros plans précédente/actuelle/suivante,
  autre étape à la même couche, cadres rouges, décision et commentaire.
- Export JSON des décisions et HTML des indications retenues. Le HTML
  inclut ses vignettes et peut être imprimé depuis un navigateur.

Le moteur ne dépend pas d'Internet. Le téléchargement des exemples est
un script séparé, exécuté explicitement.

## Démarrer

Python 3.10 ou plus récent avec NumPy et Pillow est nécessaire :

```powershell
python -m pip install -r requirements.txt
python inspector.py analyze datasets/nist_sample results_nist_16bit --config config.nist_sample.json
python inspector.py status results_nist_16bit
python inspector.py review results_nist_16bit --limit 100
```

Ouvrir ensuite `results_nist_16bit/review_000000.html` dans un navigateur.
Les boutons permettent de sauvegarder les décisions JSON ou d'exporter
les indications retenues **sur la page courante**. Le périmètre et les
images non évaluées sont indiqués dans le rapport. Pour la page suivante :

```powershell
python inspector.py review results_nist_16bit --offset 100 --limit 100
```

Les décisions saisies dans la page ne sont pas automatiquement conservées
à sa fermeture. Télécharger le JSON avec le bouton dédié, puis le charger
dans le projet pour enregistrer les choix et leur historique :

```powershell
python inspector.py decisions results_nist_16bit chemin/decisions.json
python inspector.py review results_nist_16bit --retained-only
```

Un JSON d'un autre projet ou d'une indication modifiée après reprise est
refusé. Les commentaires sont échappés à l'export HTML.

Sur ce poste Codex, le Python fourni est disponible à l'emplacement :

`C:/Users/gogov/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`

Il possède déjà les deux bibliothèques. Les commandes ont été testées
avec ce Python 3.12.14 ; aucun Python n'est actuellement enregistré par
le lanceur Windows `py`.

## Adapter aux images de la machine

Le fichier d'exemple fixe 60 µm et une convention d'origine : couche 1
à Z = 0,060 mm. L'origine devra être ajustée selon les exports machine.
Le motif de nom de fichier est **un exemple**, pas une déduction de votre
organisation actuelle. Il doit reconnaître le chemin relatif complet,
avec les groupes `camera`, `layer` et `phase`.

Exemple reconnu : `cam1_layer00125_spread.jpg`. Les alias des étapes sont
configurables et doivent aboutir à `etalement` ou `fusion`.
Les images non reconnues sont comptées et listées dans le projet. Deux
images reconnues pour la même caméra/étape/couche rendent l'import ambigu
et bloquent l'analyse. Une interruption de la numérotation réinitialise
l'historique ; les couches ne sont pas renumérotées.

Placer les résultats dans un dossier séparé des sources. Les originaux
ne sont ni copiés ni modifiés par le moteur. Les paramètres sont figés
par projet : utiliser un autre dossier de résultats pour un autre réglage.
La reprise vérifie taille et date des sources ; elle ne calcule pas le
hachage intégral de plusieurs téraoctets.

## Limites connues et travail prévu

- Import de dossiers locaux disponible dans le navigateur ; la lecture
  des noms et les alias doivent être adaptés à l'export machine.
- La 3D utilise des plans d’aperçu espacés pour borner sa mémoire ; ce rendu
  ne contient pas toutes les couches simultanément. La coupe permet de charger
  chaque couche mesurée individuellement.
- Pas de recalage géométrique ni de surveillance validée du déplacement
  des caméras ; aucune correction de perspective ou fusion multi-caméras.
- Pas de masque CAO ni de compensation du balayage alterné. Les sections
  extraites par contraste restent approximatives et ne sont pas utilisées
  comme masque de détection. Des changements normaux peuvent produire des indications.
- Référence interne initiale sans qualification de son état. Pas de
  détection temporelle pendant l'initialisation ; une anomalie déjà présente
  au début peut rester invisible.
- Les extrema aident à voir des changements petits et contrastés, mais
  sont sensibles au bruit et au JPEG. La résolution minimale de détection
  reste à mesurer sur les images de production.
- Une dérive d'éclairage est signalée comme changement global ; le
  logiciel n'attribue pas automatiquement ce changement à une cause.
- Le regroupement entre couches est simple et peut fragmenter des
  indications mobiles ou fusionner des événements proches.
- Les mesures intermédiaires croissent avec le nombre de couches. La RAM
  contient une image et un historique de grilles ; la taille du cache et
  les performances sur plusieurs téraoctets restent à mesurer.
- Lors d'une reprise, l'historique est reconstruit depuis les mesures
  mises en cache. Les anciennes images ne sont pas redécodées pour l'analyse.
  L'estimation de durée reste indicative, notamment lorsque cette phase
  de reprise laisse place à la lecture de nouvelles images.
- Une image illisible est enregistrée comme non analysée ; le traitement
  terminé ne signifie pas que toutes les images ont été analysables.
- La comparaison entre jobs, le maillage géométrique 3D métrique, les courbes interactives
  par zone et le rapport consolidé de très grandes revues restent à développer.

## Vérification

```powershell
python -m unittest discover -s tests -v
node tests/test_stack.cjs
node tests/test_stack_controls.cjs
node tests/test_review_ui.cjs
node tests/test_review_navigation.cjs
```

Les tests couvrent la séparation des caméras et étapes, les changements
locaux/globaux, les dérives lentes, les couches manquantes, les fichiers
corrompus ou ambigus, la reprise sans redécodage, les hauteurs, les ROI,
la conversion fixe 16 bits et la persistance des décisions.
Ils couvrent aussi le lancement du moteur depuis l'interface locale,
la revue, l'export, et le refus d'une décision provenant d'un ancien
contexte d'analyse, le cadrage commun, les images de dimensions différentes,
le filtrage d'une seule étape, l'inventaire étendu et les hauteurs des plans
photographiques, la sélection de bibliothèques et les indications 3D.
Les vérifications JavaScript couvrent la projection des repères, les filtres,
la coupe, la sélection et la passe rouge après les photographies.
Les routes HTTP et les images de contexte ont été vérifiées sur un serveur
isolé avec `research/verify_upgrade.py`, sans modifier la revue active.

Un premier passage complet sur les 20 PNG publics NIST est décrit dans
la note de données. Cela vérifie l'exécution de la chaîne, pas une
performance de détection de défauts.

Les scores, le tri et la navigation sont vérifiés sur des cas synthétiques,
puis sur les sept bibliothèques avec `research/verify_priority_shape.py`.
Les masques sont contrôlés sur des sections texturées synthétiques, du fond
uniforme, des gradients et les photos réelles NIST/ORNL (8 et 16 bits).
Les tests JavaScript simulent le DOM et WebGL : ils contrôlent les couleurs,
l'alpha des sections, l'ordre de dessin, les chargements tardifs et les limites
des caches. Ils ne remplacent pas un contrôle visuel dans le navigateur.

## License

Powder Ranger is released under the MIT License. See [LICENSE](/../LICENSE).

