# Plan de tests — démonstrateur et critères d'acceptation

| Identifiant | Scénario | Attendu | Statut prototype |
|---|---|---|---|
| T01 | Import de l'échantillon synthétique (440 lignes) | 434 lignes conservées, 5 invalides, 1 doublon | Automatisé |
| T02 | Modalité non prévue | Ligne écartée, rapport qualité renseigné | Automatisé |
| T03 | Import fichier interdit `.exe` | HTTP 422, état du précédent import conservé | Automatisé |
| T04 | Identifiant répondant | Exclu des modalités et exports | Automatisé |
| T05 | Regroupement 18-24 et 25-34 | Groupe « Jeunes », fichier source immuable | Automatisé |
| T06 | Même modalité dans 2 groupes | Refus explicite | Automatisé |
| T07 | Cible à plusieurs conditions ET | Intersection des répondants | Automatisé |
| T08 | Tableau croisé, χ² et V | Résultats cohérents avec SciPy | Automatisé |
| T09 | Cellule non nulle inférieure à 10 | Aucun tableau, graphe, statistique ou export | Automatisé |
| T10 | Export agrégé CSV | Aucun identifiant, valeurs injectables échappées | Automatisé |
| T11 | Sauvegarde de configuration | JSON sans réponses ; restauration sur même empreinte | Automatisé |
| T12 | Sauvegarde et fichier différent | Refus explicite | Automatisé |
| T13 | Sessions de deux navigateurs | Données isolées en mémoire | Automatisé |
| T14 | Interface clavier et lecteur d'écran | Navigation accessible | À vérifier manuellement |
| T15 | Utilisateur non autorisé | Accès impossible | **Non implémenté** |
| T16 | Données personnelles, réidentification par requêtes successives | Risque maîtrisé et validé | **Non garanti** |
| T17 | Tests de charges 10, 50, 100 utilisateurs | Temps de réponse acceptable | À mesurer |
| T18 | Questions numériques, multi-réponses et pondérations | Méthode statistique adaptée | Hors périmètre v0.1 |

| T19 | Archive chiffrée `.sae` | AES-GCM et phrase secrète longue, restauration après nouvelle session | Automatisé |
| T20 | Mauvaise phrase secrète | Refus sans modification de l’enquête courante | Automatisé |

Lancer les tests automatisés : `pytest -q`.

## Recette métier proposée

1. Importer un jeu de référence donné par Sodebo et comparer les exclusions avec le traitement de l'institut.
2. Créer un regroupement de modalités, puis reproduire un résultat connu par l'équipe Études.
3. Construire une cible avec deux filtres et vérifier la population calculée.
4. Comparer une table et la p-valeur avec l'outil statistique actuellement validé par Sodebo.
5. Vérifier le seuil de diffusion et l'absence de données individuelles dans tous les exports.
6. Restaurer la configuration de projet après réimport du jeu de données.

**Décision de mise en production : impossible avec cette seule version démonstrateur.** Nécessite un audit RGPD/sécurité, une recette statistique, une stratégie de stockage et l'autorisation du client.