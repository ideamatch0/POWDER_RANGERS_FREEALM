# Cadrage de la première version

Décisions issues de l'échange du 8 septembre 2026 : LPBF métallique,
photos après étalement et après fusion, caméras fixes avec dérives possibles,
plusieurs téraoctets de JPEG probables, analyse après fabrication sur PC
standard. Épaisseur habituelle : 60 µm. Pas de job de référence qualifié.
La géométrie ne sera pas intégrée au premier essai. La comparaison entre
jobs vient ensuite. Un empilement photographique 3D a été ajouté à la
démonstration à la demande de l'utilisateur.

## Objectif utilisateur

Réduire le nombre d'images à examiner en proposant des régions ayant changé
d'aspect. L'opérateur décide quelles indications retenir. Le rapport final
présente ces indications, leur localisation et leur contexte, en indiquant
la couverture effective de l'analyse.

## Organisation proposée

1. **Import** : dossier source, numérotation des couches, caméra/canal,
   étape, Z, détection des doublons et des fichiers absents ou illisibles.
2. **Préparation** : définir une ROI par caméra ; garder les étapes
   séparées, avec choix d'analyser l'une ou les deux ; conserver une échelle
   lumineuse cohérente. Prévoir ensuite
   un recalage reposant sur des régions fixes distinctes des pièces.
3. **Mesures** : traiter les images une à une ; extraire des grilles
   compactes de luminosité/dispersion/contraste ; sauvegarder les mesures
   pour relancer ou reprendre sans redécoder les JPEG.
4. **Indications** : écart brusque par rapport aux couches voisines
   comparables ; dérive depuis une référence interne de départ ; suivi
   séparé de la luminosité globale. Regrouper les régions et les couches.
5. **Revue** : image repère avec surimpression désactivable, gros plans
   N−1/N/N+1 au même cadrage et autre étape à N, décision/commentaire.
   La courbe de la zone reste à développer.
6. **Rapport** : indications retenues, couches et Z, coordonnées image,
   caméra/étape, photos annotées, réglages et couverture réelle.
7. **Empilement 3D** : plans photographiques d'une seule étape et caméra,
   textures réduites, rotation, zoom et coupe par couche. Aucune fusion
   des éclairages, aucune interpolation des couches manquantes.

Les unités XY restent des pixels tant qu'une calibration vers le plateau
n'est pas disponible. L'empilement actuel utilise Z en millimètres, avec
une amplification visuelle de cet axe et des coordonnées X/Y en pixels.
Une reconstruction de surfaces ou de défauts internes à partir de la
luminosité n'est pas réalisée.

## Méthodes candidates et phénomènes visibles

La littérature présente des stries/sauts du racleur, des zones mal
recouvertes, des dépôts de projections ou débris, des surélévations et
des changements d'aspect de la surface fusionnée. Les photos peuvent
contenir les signatures de ces phénomènes sans permettre une
classification causale fiable dans toutes les conditions.

Le prototype commence par des indicateurs temporels de luminosité et
de contraste. Les filtres orientés pour les stries, les mesures de texture
plus détaillées et les comparaisons appariées avant/après exposition
seront évalués ensuite sur des exemples réels. La différence entre
étalement et fusion sert d'abord au contexte : elle contient aussi
la transformation normale de la matière.

Sources :

- [NIST IR 8538, 2024](https://nvlpubs.nist.gov/nistpubs/ir/2024/NIST.IR.8538.pdf),
  notamment la section 3.2.2 : signatures visibles en imagerie de lit de poudre.
- [Boschetto et al., 2023/2024](https://doi.org/10.1007/s10845-023-02091-7),
  traitement numérique d'images de lit de poudre sur machine SLM.
- [NIST, cartes EWMA](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm),
  fondement statistique du suivi des petites évolutions persistantes.

## Validation attendue avant emploi sur un job complet

- Examiner des séquences normales : géométrie évolutive, alternance
  de balayage, différences de brillance entre phases, zones saturées.
- Examiner des indications connues et des changements synthétiques
  clairement identifiés comme tels pour tester séparément le fonctionnement.
- Mesurer le nombre de régions à revoir par 1 000 couches, les indications
  connues retrouvées ou manquées, le temps de calcul, la RAM maximale et
  le volume du cache. Aucune performance cible chiffrée n'est encore prouvée.
- Vérifier que les résultats après reprise sont identiques à ceux d'une
  analyse continue et que les images manquantes restent visibles au rapport.

## Informations encore nécessaires pour l'import industriel

Quelques chemins/noms réels permettant de reconnaître la caméra, la couche
et l'étape ; résolution des JPEG ; convention d'origine de Z. L'épaisseur
de 60 µm est connue. Ces informations ne bloquent pas les premiers essais
sur les séquences publiques NIST.


## Analyse Aalto d'un job seul

Depuis l'harmonisation du 9 septembre 2026, `inspector.extract` et `Detector`
sont partagés par les imports documentés et Aalto. La moyenne photométrique
utilise tous les pixels du cadrage, sur une échelle fixe 0–255. Chaque
caméra/étape ou séquence calibre ses 20 premières images dans le même job.
Le profil fixe uniquement le gris de départ ; son écart type ne détermine
pas les seuils. La comparaison au gris initial commence après ces 20 images,
tandis que les détections temporelles commencent après l'historique minimal.
Les réglages utilisateur et la variabilité temporelle pilotent la sensibilité.

`job_views.py` adapte les acquisitions Aalto au même contrat de revue que
les autres imports : `/api/events`, `/api/event`, `/api/image`, `/api/decision`,
`/api/stack` et `/api/stack-image`. L'interface utilise un unique affichage
avec cadre bleu de contexte, trois gros plans et sélection des repères 3D.
Les positions Aalto utilisent `position=counter`, `axis=acquisition`,
`z_mm=null`. Les métadonnées complètes des acquisitions restent accessibles ;
seuls environ 128 aperçus sont chargés d'avance. La coupe charge sa photo
à la demande, avec un cache graphique borné à 160 textures.

Le moteur documenté passe en version 0.2.0 et l'analyse Aalto en single-job-2.
Les anciens résultats et décisions restent dans leurs dossiers ; les nouveaux
calculs ont des identifiants distincts. Les mesures Aalto compatibles sont réutilisées.

Trois entrées de catalogue représentent trois jobs disjoints. Les originaux
restent dans un dossier commun. L'inventaire sélectionne le job, retire tous
les champs d'annotation, puis calcule une empreinte sur ses seuls fichiers
et métadonnées d'acquisition. Changer un autre job ou ses labels ne modifie
pas cette empreinte.

`job_analysis.py` calibre le niveau moyen de gris sur les 20 premières
acquisitions de chaque séquence. L'intervalle explicite 1 ou 2 définit les
séquences ; il ne détermine aucune étape physique. Chaque séquence possède
un `Detector` indépendant, avec médiane/MAD temporelles et dérive EWMA.
La luminosité de chaque image est soustraite des canaux de contraste local
et surveillée séparément. La calibration globale utilise uniquement ce job.

`POST /api/calibrate` prépare le gris seul. `POST /api/analyze` calibre si
nécessaire puis analyse toutes les images du job sélectionné. Les réglages,
le cadrage, l'intervalle et la version du moteur identifient les résultats.
Le bilan sépare images mesurées, évaluées, d'initialisation et illisibles.
Les discontinuités réinitialisent uniquement l'historique concerné.

Les mesures compressées en SQLite et les JSON atomiques sont propres à
chaque bibliothèque dans `job_runs/`. Une interruption garde le cache et
le dernier résultat complet. Les décisions sont identifiées par empreinte
d'analyse, job, image et prédiction dans `aalto_runs/review.sqlite`.
Les cadres rouges proviennent exclusivement du calcul courant ; les gros
plans voisins utilisent le cadrage de l'indication et l'intervalle choisi.

Le mode de comparaison à un job de référence est présenté avant le choix
de bibliothèque, clairement indisponible. Aucun ancien profil de validation
croisée n'est utilisé. `aalto_calibration.py` et [CALIBRATION_AALTO.md](CALIBRATION_AALTO.md)
restent des archives expérimentales indépendantes de l'application.

## Persistance et navigation de revue

`min_consecutive` est un réglage de revue (1–10 000), sauvegardé par bibliothèque
hors `Config`. `POST /api/review-settings` l'applique sans changer les identifiants
d'analyse, le cache ni les décisions. Les résultats SQL regroupés utilisent leur
durée `end_layer-start_layer+1`. Pour les occurrences Aalto, `persistence.py`
construit des liens de recouvrement entre acquisitions immédiatement voisines
d'une même caméra, séquence, catégorie et géométrie. Deux parcours calculent la
plus longue chaîne passant par chaque occurrence, afin qu'une branche courte
n'hérite pas indûment de la durée entière d'un groupe. Ce calcul est mis en cache
par signature d'analyse et ne dépend pas des décisions de l'opérateur.

Les mêmes durées filtrent `/api/events`, `/api/stack` et les deux exports HTML.
Le bilan JSON conserve les mesures brutes et ajoute le réglage de revue.
`GET /api/events?after=…` cherche le successeur dans l'ordre et les filtres actifs
après enregistrement, puis fournit `next_id` et la page correspondante. Cette
recherche reste correcte quand le statut modifié retire l'indication de la liste.
Le navigateur interdit les doubles sauvegardes et n'avance qu'après leur succès.
