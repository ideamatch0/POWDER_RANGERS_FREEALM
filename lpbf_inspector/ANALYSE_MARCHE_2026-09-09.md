# Surveillance LPBF : offres actuelles et évolution du prototype

Analyse ciblée au 9 septembre 2026. Périmètre : inspection du lit de poudre,
exploitation des images de couches et revue après fabrication. Les capacités
commerciales ci-dessous sont celles annoncées par les fournisseurs ; elles
n'ont pas été évaluées sur vos données. Il ne s'agit pas d'une comparaison
de performances de détection ni d'une étude de parts de marché.

## Ce que proposent les acteurs pertinents

| Solution | Positionnement et fonctions annoncées | Intérêt pour votre usage | Conditions à vérifier |
|---|---|---|---|
| **Interspectral — AM Explorer** | QUALIFY : rapprochement de données de procédés, visualisation 3D, annotations et rapports. DETECT : module de détection par IA, avec calcul GPU. MONITOR : suivi pendant fabrication et alarmes. | Référence particulièrement pertinente pour une revue après job : sélectionner une indication, la retrouver dans le volume et documenter sa décision. | Connecteur pour la machine, formats réellement disponibles, architecture locale et ressources matérielles. DETECT nécessite QUALIFY ou MONITOR ; vérifier la disponibilité selon la machine. |
| **Materialise — Quality & Process Control / Layer Analysis** | Plateforme de corrélation des données de qualité et de procédé ; analyse de couches par IA, localisation sur des modèles 3D et suivi du procédé. | Intéressant lorsque les photos doivent être reliées aux paramètres machine, aux essais matière et aux résultats de contrôle. | Étendue du projet d'intégration CO-AM, accès aux données, hébergement, licences et compatibilité des équipements. |
| **EOS — Smart Monitoring / EOSTATE Exposure OT / Smart Fusion** | Surveillance par tomographie optique et intégration avec la régulation de la puissance laser. | Exemple de séparation entre observation, analyse et action sur la fabrication. | Offre liée à l'écosystème EOS et au matériel OT. Les informations thermiques et la boucle de régulation ne sont pas récupérables depuis de simples JPEG du lit. |
| **Renishaw — InfiniAM Camera et Spectral** | Camera exploite les photos après apport de poudre et après fusion. Spectral propose des cartes 2D/3D d'énergie et d'émissions, avec les capteurs LaserVIEW/MeltVIEW. | Très proche de votre distinction entre les deux étapes ; utile pour penser la navigation par couche et la comparaison de jobs. | Compatibilité RenAM 500, capteurs installés et possibilités d'export. |
| **ADDIGURU** | Surveillance in situ, traitement de signaux optiques, thermiques et machine, détection IA/ML et rapports. Positionnement annoncé indépendant des machines et matériaux. | Référence pour hiérarchiser les événements et concentrer l'attention de l'opérateur. | « Indépendant » ne dispense pas de vérifier l'intégration et les performances sur la machine et les données réelles. |
| **Phase3D — Fringe Inspection** | Mesure de topographie par projection de lumière structurée ; cartes de hauteur par couche. | Montre l'intérêt de distinguer une variation d'aspect d'une variation géométrique mesurée. | Nécessite une acquisition spécifique avec projection. Cette mesure ne peut pas être ajoutée a posteriori aux JPEG existants. |

Sources officielles correspondant aux lignes du tableau :

- [Interspectral : gamme AM Explorer](https://interspectral.com/solutions-am-explorer/am-explorer-platform/) et [QUALIFY](https://interspectral.com/solutions-am-explorer/qualify/).
- [Materialise : Quality & Process Control](https://www.materialise.com/en/industrial/software/quality-process-control).
- [EOS : Smart Monitoring](https://www.eos.info/fr/chaine-de-solutions/software/eos-smart-monitoring).
- [Renishaw : InfiniAM Camera et Spectral](https://www.renishaw.com/hu/infiniam-spectral--42310).
- [ADDIGURU : offre et fonctions](https://www.addiguru.com/).
- [Phase3D : technologie Fringe](https://www.phase-3d.com/pages/fringe-technology).

Ces offres appartiennent à deux familles distinctes : logiciels d'exploitation
et de revue des données, et systèmes associant capteurs, machine et parfois
commande du procédé. Votre besoin actuel relève surtout de la première.
Le fait que plusieurs offres utilisent l'IA ne rend pas l'apprentissage
nécessaire pour améliorer la navigation, la traçabilité ou le suivi de
variations de luminosité.

## Coût et comparaison achat / développement

Les pages consultées ne donnent pas de tarif directement comparable pour
un périmètre équivalent à votre projet. Je ne propose donc pas de prix estimé.
Un devis utile devrait distinguer : licence, import des données de votre
machine, intégration, matériel éventuel, stockage, maintenance et formation.
Il faudrait également vérifier la capacité à fonctionner hors ligne et à
réexporter les données et les décisions.

Le prototype local répond à un périmètre plus restreint : revue après
fabrication à partir des photos disponibles, sans abonnement ni service
externe nécessaire au calcul. Son coût réel reste celui du développement,
de l'adaptation aux exports machine et de la validation. Il ne remplace pas
une chaîne industrielle qualifiée ni les mesures de capteurs absents.

## Fonctions que je recommande

Les priorités suivantes sont mon appréciation technique de votre besoin.

| Priorité | Fonction | Bénéfice attendu | État / effort relatif |
|---|---|---|---|
| Immédiate | Thème sombre, hiérarchie lisible, gros plans synchronisés | Réduire la fatigue de lecture et les recherches visuelles | Intégré à cette évolution ; les intensités des photos restent inchangées |
| Immédiate | Indications rouges dans la 3D, clic vers la revue 2D, filtres par décision et couche | Retrouver une zone dans le job et accéder à sa preuve photographique | Intégré ; localisation au plan de l'indication maximale, sans inventer une étendue volumique |
| Immédiate | Bibliothèques distinctes et import local paramétrable | Tester plusieurs acquisitions tout en séparant données, paramètres et décisions | Intégré ; références aux fichiers sans copie des images de production |
| Haute | Courbes temporelles sur une zone, avec luminosité globale et score | Comprendre ce qui a déclenché une indication et distinguer saut et dérive | Prochaine étape ; effort modéré, cache de mesures déjà disponible |
| Haute | Masques de pièces et de zones à ignorer, dessinés sur une photo | Réduire les indications sur le racleur, les reflets ou les zones hors plateau | Prochaine étape ; effort modéré, validation opérateur du masque |
| Haute | Diagnostic de qualité d'acquisition : saturation, flou, dérive lumineuse et déplacement | Distinguer une évolution du procédé d'une image devenue peu comparable | À développer ; recalage à valider sur des repères fixes |
| Moyenne | Regroupement des événements proches et classement par persistance, surface et amplitude | Éviter de revoir de nombreux cadres correspondant au même phénomène | À développer ; effort modéré, sans interpréter le score comme une probabilité de défaut |
| Moyenne | Revue par pièce et rapport incluant couverture, exclusions et historique des décisions | Faire un rapport exploitable et expliquer ce qui n'a pas été évalué | Rapport de base existant ; identification des pièces à ajouter |
| Ultérieure | Comparaison de fabrications répétées avec une référence qualifiée | Repérer les changements propres à un job | Dépend d'une référence et d'un recalage fiables |
| Ultérieure | Croisement avec CAO, tomographie et journaux machine | Rechercher les causes et valider les signatures observées | Effort élevé, disponibilité des données et calibration nécessaires |

Je donnerais la priorité suivante aux courbes temporelles et aux masques
de zones. Ces deux fonctions devraient apporter davantage à votre capacité
d'interprétation qu'un nouveau détecteur opaque.

## Second jeu de données et limites de comparaison

Le jeu [Aalto / EOS M290](https://zenodo.org/records/14996806), publié par
Xinyi Yin, Jan Sher Akmal, Mika Salmi et Roy Björkstrand (2025, CC BY 4.0),
contient des photos PB et des annotations manuelles. L'archive originale a
été téléchargée et son MD5 vérifié. Les 2 638 photos PB sont intégrées à la
galerie ; les images OT sont séparées et ne sont pas mélangées à ces photos.

Les noms permettent de distinguer trois jobs et des compteurs d'acquisition.
Ils ne suffisent pas, dans les vérifications effectuées, à attribuer avec
certitude une étape et une hauteur à chaque photo. La galerie propose donc
les annotations d'origine et leurs gros plans, tandis que le calcul temporel
et la 3D à Z physique restent disponibles pour les séries dont la
correspondance couche/étape est définie, notamment le NIST et les imports
locaux configurés. Les annotations Aalto ne sont jamais présentées comme
des détections de notre moteur.

Cette collection est utile pour examiner la diversité des signatures et
préparer une évaluation. Elle ne fournit pas, à elle seule, une validation
des performances de détection du prototype.
