# DOSSIER D'ANALYSE — SAÉ 5.01

**Projet : Sodebo Survey Analytics — Outil décisionnel pour l'analyse interactive d'enquêtes**  
**Client mentionné dans le sujet : Sodebo**  
**Statut : proposition pédagogique non validée par le client**  
**Version : 0.1, novembre 2026 — année universitaire 2026–2027 supposée**

## 1. Contexte et problématique

Sodebo commande des enquêtes auprès d'entreprises spécialisées. À réception, ses collaborateurs disposent d'une structure de questionnaire et d'un ensemble de réponses. Les analyses doivent être renouvelées avec des regroupements et des sous-populations définis par les utilisateurs. L'outil demandé doit réduire les manipulations manuelles, rendre les choix reproductibles et offrir une restitution lisible avec des tests statistiques adaptés.

**Problème :** comment permettre à une personne possédant des bases en analyse de données, sans obligation de programmer, de produire des tableaux, graphiques et analyses fiables, paramétrables et suffisamment protecteurs pour les répondants ?

**État de l'existant :** le nom du logiciel utilisé actuellement par Sodebo n'est pas confirmé. Un cas académique CCMP sur Sodebo indique l'emploi de Sphinx pour un exercice d'analyse de 306 questionnaires, mais **cela ne démontre pas une utilisation interne actuelle**. Une réunion de cadrage devra identifier les outils réellement en place, les attentes de compatibilité et les limites de l'existant.

## 2. Objectifs métier et périmètre

Objectifs : importer des résultats de sondages, contrôler leur qualité, constituer des regroupements de modalités, définir des cibles par intersections ou unions, produire des analyses comparatives, associer des tests d'hypothèses, sauvegarder la configuration de travail et limiter la divulgation de résultats sensibles.

**Dans le périmètre prototype :** CSV/XLSX, structure JSON optionnelle, variables catégorielles/ordinales, suppression des lignes invalides, exclusion des identifiants, recodages, cibles AND/OR, tableau croisé, histogrammes, khi-deux/Fisher, export de tableaux agrégés, sauvegarde de paramètres, archive chiffrée de session.

**Hors périmètre prototype :** comptes utilisateurs et rôles, SSO, sauvegarde automatique et multi-utilisateurs des réponses côté serveur, base de données centralisée, pondérations, plans d'échantillonnage complexes, tests multiples avancés, questions numériques continues, traitement multichoix, analyses textuelles, audit RGPD complet et déploiement en production.

## 3. Parties prenantes et utilisateurs

- **Commanditaire Sodebo / responsable Études** : priorise les fonctions, accepte les règles statistiques, valide les livrables.
- **Analyste métier** : importe les fichiers, nettoie selon la politique validée, crée groupes/cibles, analyse et exporte.
- **Administrateur informatique** : futur rôle de gestion des accès, sauvegardes, hébergement et sécurité.
- **Équipe SAÉ** : recueille le besoin, développe, documente, teste et soutient la solution.
- **Référent conformité** : contrôle le traitement des données personnelles et le risque de réidentification.

## 4. Exigences fonctionnelles — priorités MoSCoW

| ID | Besoin | Priorité | Critère de validation |
|---|---|---|---|
| F01 | Importer réponses et structure | Must | CSV/XLSX et JSON acceptés ou erreur compréhensible |
| F02 | Nettoyer les réponses | Must | Rapport du nombre de lignes invalides et de doublons |
| F03 | Regrouper les modalités | Must | Plusieurs modalités fusionnées sans toucher à l'original |
| F04 | Créer des cibles | Must | Conditions AND/OR, cibles réutilisées dans l'analyse |
| F05 | Générer des tableaux et graphiques | Must | Tableau cohérent avec le graphique, effectifs visibles |
| F06 | Tester les hypothèses | Must | Test, H₀, statistique, p-valeur et limites affichés |
| F07 | Protéger les petites cellules | Must | Aucun résultat visible si une cellule non nulle < 10 |
| F08 | Sauvegarder une configuration | Must | Paramètres rechargés sur même fichier ; archive chiffrée complète possible |
| F09 | Exporter les résultats agrégés | Should | CSV sans réponses individuelles |
| F10 | Gérer les comptes et droits | Should en S6 | Authentification et rôles contrôlés |
| F11 | Gérer données pondérées et multi-réponses | Could | Implémentation selon les exemples de fichiers réels |
| F12 | Produire un PDF de rapport | Could | Export sur modèle métier approuvé |

Must = indispensable ; Should = fortement souhaitable ; Could = amélioration sous réserve de temps. **F07 est un premier garde-fou, pas une garantie totale d'anonymisation.**

## 5. Contraintes non fonctionnelles

- **Ergonomie :** interface en français, ordonnée en cinq étapes, utilisable sans langage de programmation.
- **Fiabilité :** calculs centralisés dans un module isolé et testable ; rejets d'import explicites ; fichiers sources non réécrits.
- **Traçabilité :** rapport de nettoyage, configuration des groupes/cibles versionnée ; historique de modifications à ajouter.
- **Sécurité :** données personnelles éliminées de la mémoire analytique quand repérables ; résultat masqué en dessous de dix observations par cellule non nulle ; déploiement sur réseau interne recommandé.
- **Qualité scientifique :** préconditions des tests vérifiées ; si non satisfaites, résultat signalé comme fragile/non applicable ; correction des tests multiples à étudier.
- **Disponibilité :** à négocier pour le déploiement ; le démonstrateur fonctionne localement sans stockage de production.
- **Performance :** limite démonstrateur de 100 000 réponses, 100 colonnes, 12 Mo ; temps de réponse à mesurer sur données réelles.

## 6. Processus cible et scénarios

**Flux principal :** fournisseur de sondage → import des réponses et questionnaire → validation/nettoyage → sélection des variables → regroupement des modalités → définition des cibles → calcul des tableaux et tests → vérification de confidentialité → visualisation et export agrégé → sauvegarde de configuration.

**UC01 Analyser une enquête :** un analyste importe deux fichiers ; le système valide et déclare les exclusions ; l'analyste regroupe les tranches d'âge, définit « jeunes acheteurs hebdomadaires », croise le groupe avec l'intention d'achat, consulte le tableau, le graphique et la p-valeur ; il exporte un agrégat si le seuil de publication est respecté.

**UC02 Reprendre une analyse :** l'analyste revient avec le même fichier de réponses ; il réimporte le fichier et recharge la configuration JSON. Le système vérifie l'empreinte SHA-256 avant de restaurer regroupements et cibles.

**UC02 bis Archive chiffrée :** l’analyste choisit une phrase secrète, télécharge une archive `.sae` contenant les réponses nettoyées et les paramètres, puis restaure le projet sur une nouvelle session en fournissant le fichier et la même phrase. Il reste responsable de la protection de cette archive.

**UC03 Refus de divulgation :** une combinaison produit une cellule de moins de dix individus. Le système ne renvoie ni effectif, ni graphique, ni résultat de test, ni export pour ce tableau.

## 7. Architecture retenue et justification

Le prototype adopte une architecture trois composants : **frontend HTML/CSS/JavaScript** → **API Python FastAPI** → **moteur pandas / SciPy**. Les réponses sont conservées en mémoire dans une session navigateur. Les exports CSV/JSON standards ne contiennent aucune réponse individuelle. Une **archive locale chiffrée facultative** permet de sauvegarder les réponses nettoyées (encore potentiellement réidentifiables), indépendamment de la configuration exportée séparément.

Alternatives étudiées : **Shiny pour Python**, qui permet un développement rapide d'interfaces statistiques intégrées, et **application desktop Python**, dont le déploiement sur les postes peut être plus complexe. FastAPI + JavaScript a été retenu pour rendre explicites l'API, les contrôles d'accès futurs et la testabilité du moteur indépendant de l'interface. Ce choix doit être validé avec Sodebo et ses contraintes SI.

Modules : `ingest` (import / qualité), `transformed` (regroupements), `target_mask` (filtrage), `analyze` (tableaux et inférences), `aggregate_csv` (export sécurisé), serveur HTTP (`main.py`) et interface (`app/static/`).

## 8. Modèle de données logique

- **Enquête** : fichier source, empreinte SHA-256, schéma, rapport qualité, réponses exploitables en mémoire.
- **Question** : identifiant, libellé, type, obligation, modalités autorisées, marqueur identifiant.
- **Regroupement** : variable, nom de groupe, liste non recouvrante de modalités.
- **Cible** : nom, opérateur AND/OR, liste de conditions variable/valeurs.
- **Analyse** : variable principale, comparaison optionnelle, cible optionnelle, seuil alpha et résultat calculé à la demande.
- **Session** : configuration versionnée liée à l'empreinte d'un fichier, ou archive complète chiffrée des réponses nettoyées et des paramètres.

**Règles d'intégrité :** les valeurs regroupées doivent appartenir à la variable ; une modalité ne peut appartenir à deux regroupements ; les cibles n'utilisent que les modalités courantes ; l'analyse n'utilise ni identifiant ni champ libre.

## 9. Méthodologie statistique

**Nettoyage :** rejet complet des lignes comportant un champ obligatoire vide/non renseigné, ou une modalité invalide si une liste est déclarée ; retrait des doublons par premier identifiant ; rapport d'exclusions. Ce choix suit le besoin exprimé, mais devra être revu avec le client car supprimer toutes les lignes incomplètes peut introduire un **biais de sélection**.

**Tableau croisé catégoriel :** test du khi-deux d'indépendance (H₀ : variables indépendantes). La table de contingence contient les effectifs observés ; `SciPy` fournit la statistique, les degrés de liberté, les effectifs attendus et la p-valeur. V de Cramér renseigne la force de l'association. En tableau 2×2 avec faibles effectifs attendus, utilisation du test exact de Fisher. Lorsque les effectifs attendus sont insuffisants pour un tableau plus grand, le résultat est signalé non interprétable sans test adapté.

**Une variable, aucune cible :** test du khi-deux d'adéquation à une distribution uniforme, **uniquement comme hypothèse technique explicitée**. Son intérêt métier n'est pas présumé ; une distribution de référence fournie par le client serait préférable.

**Une variable et une cible :** test d'homogénéité/indépendance par tableau « cible vs hors cible », à interpréter selon le plan d'échantillonnage et la comparabilité des sous-populations.

**Attention :** aucune causalité déduite, vérification de l'indépendance des observations, de la méthode d'échantillonnage, des pondérations, de la multiplicité des tests et de la représentativité de l'enquête nécessaire.

## 10. Confidentialité, anonymat et risques

L'anonymat ne se résume pas à retirer le nom ou à masquer les effectifs. Les variables indirectement identifiantes, les requêtes répétées, les comparaisons entre sous-cibles et les exports peuvent permettre des inférences. Le prototype supprime des colonnes directes détectées, évite de retourner des réponses individuelles via les analyses et les exports standard, et **bloque la sortie entière** lorsqu'une cellule non nulle d'un tableau contient de 1 à 9 individus. Cette suppression complète évite une reconstruction simple par les totaux du même tableau, mais **pas les attaques par requêtes différentielles entre plusieurs analyses. L’archive chiffrée complète contient des microdonnées et suppose une phrase secrète robuste et une conservation maîtrisée**.

Le prototype n'est **pas** conforme par défaut à un usage en production de données personnelles. Mesures S6 obligatoires : revue des catégories personnelles, minimisation, finalités et durée de conservation, authentification, séparation des accès, journalisation, stockage/transport chiffré, limitation des requêtes, tests d'inférence différentielle et validation avec le DPO/RSSI si nécessaire. Le seuil 10 est un paramètre d'étude à confirmer auprès du client.

## 11. Maquettes et parcours d'interface

L'application concrète constitue une première maquette fonctionnelle. Elle expose cinq onglets : **1. Données & qualité, 2. Regroupements, 3. Cibles d'analyse, 4. Tableaux & tests, 5. Sauvegarde** (paramètres ou archive chiffrée). Un bloc de travail présente les filtres, un autre les résultats et un troisième explicite le test statistique. Les petites cellules affichent un message de confidentialité à la place de toute restitution.

Les captures et éventuels prototypes graphiques sont des supports de discussion, pas des écrans approuvés par Sodebo. Ergonomie à vérifier auprès des analystes : vocabulaire des questions, filtres hiérarchiques, comparaison entre cibles, préférences d'export et accessibilité.

## 12. Planning et lots

Calendrier hypothétique novembre 2026 → juillet 2027 : cadrage / dossier S5 jusqu'en janvier ; import et modèle de données février-mars ; regroupements / cibles mars-avril ; statistiques et interface avril-mai ; sessions / sécurité / exports avril-juin ; tests de recette mai-juin ; livraison et soutenances juillet. Voir `PLANNING_GANTT.md` pour le diagramme par mois et les jalons.

## 13. Risques, mesures et décisions attendues

| Risque | Impact | Mesure |
|---|---|---|
| Formats de données variables selon institut | Élevé | Échantillons réels + contrat d'import |
| Biais lié au nettoyage complet | Élevé | Validation statistique des règles et bilan des exclusions |
| Test statistique inadapté | Élevé | Guide d'utilisation, recette par référent métier |
| Réidentification par croisements | Critique | Validation RGPD, requêtes limitées, audits d'inférence |
| Stockage et authentification absents | Critique | Architecture de production à créer au S6 |
| Dérive du périmètre | Moyen | Backlog MoSCoW et validation des évolutions |
| Indisponibilité du client | Moyen | Réunions de suivi et décisionnaires désignés |

**À faire valider par Sodebo :** exemples de fichiers réponses + structures ; logiciel actuel et limites ; profils des utilisateurs ; définition métier des groupes/cibles ; bonnes hypothèses nulles ; seuils d'effectifs ; gestion des pondérations ; formats d'export ; règles de sécurité ; méthode de recette ; calendrier.

## 14. Critères de réception

La proposition S5 est recevable si le besoin est reformulé, les fonctionnalités priorisées, l'architecture et les règles statistiques justifiées, les maquettes exploitables, les risques documentés et le S6 planifié. Le S6 n'est recevable que lorsque la recette sur données client, les tests de sécurité et la conformité attendue ont été validés, en complément de la démonstration technique.

## 15. Sources publiques

1. Sodebo, « Nos métiers du développement produits – Études » : https://www.sodebo.com/recrutement/nos-metiers/developpement-produit
2. CCMP, « Sodebo : analyse des résultats d'enquête », cas pédagogique M1879 : https://ccmp.fr/collection-ccmp/cas-sodebo
3. Symetris, étude « Sodebo : test d'innovation dans les rayons ! », 2 juin 2025 : https://symetris.fr/article/sodebo-alimentaire-innovation
4. Documentation Shiny for Python : https://shiny.posit.co/py/api/core/

Sources citées à titre contextuel ; elles ne constituent ni le cahier des charges de Sodebo ni une preuve de son logiciel interne actuel.