# SAÉ 5.01 / 6.01 — Sodebo Survey Analytics

**Version 0.1 — démonstrateur local pédagogique, non validé par Sodebo.**

Application web Python (FastAPI) + JavaScript natif pour analyser les fichiers d'enquêtes avec une interface interactive. Elle propose import, contrôle qualité, recodage des modalités, définition de cibles, tableaux croisés, graphiques, tests statistiques, suppression des petites cellules et sauvegarde/restauration des configurations **et archive complète chiffrée**.

## Démarrage rapide

Pré-requis : Python 3.11+ et pip. Dans le dossier `SAE_Sodebo_Projet` :

```bash
python -m venv .venv
# Sur Linux/macOS :
source .venv/bin/activate
# Sur Windows : .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Ouvrir dans le navigateur : **http://127.0.0.1:8000**.

Cliquer sur **Charger les données de démonstration**, puis **Tableaux & tests**. Choisir `age` et `intention_achat` et cliquer **Générer l'analyse**. Les fichiers CSV/JSON d'exemple sont dans `examples/`.

Pour vérifier les traitements :

```bash
pytest -q
```

## Livrables inclus

- `app/main.py` : routes HTTP et isolation des sessions navigateur en mémoire.
- `app/secure_sessions.py` : archivage chiffré (Scrypt + AES-GCM), restauration des réponses nettoyées.
- `app/analysis.py` : import, nettoyage, validation, regroupements, cibles, statistiques et confidentialité.
- `app/static/` : interface web responsive, sans dépendance JavaScript externe.
- `examples/reponses_demo.csv` : **données synthétiques** (440 réponses, dont 5 invalides et 1 doublon).
- `examples/questions_demo.json` : structure et modalités des questions.
- `tests/` : tests de traitements et d'API.
- `docs/DOSSIER_ANALYSE.md` et `Dossier_analyse_SAE_5_01.docx` : conception de S5.
- `docs/PLANNING_GANTT.md`, `docs/PLAN_TESTS.md`, `docs/FORMAT_DONNEES.md` : outils de pilotage du S6.

## Choix techniques et limites

**Pourquoi FastAPI + JavaScript plutôt que Shiny ?** Les deux technologies conviennent à un outil interactif. Cette version retient FastAPI pour séparer le moteur d'analyse de l'interface, tester les API et pouvoir faire évoluer la partie front-end. Shiny reste une alternative documentée dans le dossier. Le logiciel réellement utilisé par Sodebo n'est **pas connu publiquement**.

**Confidentialité :** cette application masque l'ensemble d'un résultat dès qu'une cellule non nulle contient moins de 10 répondants, écarte les champs identifiants et libres de la mémoire analytique et n'exporte jamais de lignes individuelles. **Elle ne garantit pas l'anonymat au sens RGPD** : des croisements multiples, les données importées, la mémorisation en RAM ou les erreurs de configuration peuvent encore générer un risque. Pas d'utilisation sur données personnelles réelles sans validation par le responsable de traitement et durcissement de sécurité.

**Sessions :** chaque navigateur dispose d'un état en mémoire tant que le serveur est actif. Export `.json` des regroupements/cibles uniquement. La restauration nécessite le même fichier d'enquête, contrôlé par empreinte SHA-256. Il est aussi possible de télécharger une **archive `.sae` chiffrée avec une phrase secrète** (minimum 12 caractères), contenant les réponses nettoyées et les paramètres : elle permet de rouvrir le projet sans le fichier original. **L’archive contient encore des microdonnées potentiellement personnelles**, malgré l’exclusion des identifiants ; elle doit être conservée dans un lieu sûr. Pas d’authentification, de journal d’audit ni de sauvegarde automatisée côté serveur. Le mode local doit être conservé pour le prototype.

**Statistiques :** test du khi-deux d'indépendance pour les tableaux croisés, test exact de Fisher en cas de faibles effectifs attendus sur un 2×2, mise en garde si les conditions d'utilisation du khi-deux ne sont pas remplies. Pour une distribution seule, le khi-deux d'adéquation à l'uniformité est montré comme **hypothèse technique non présumée pertinente**. La pondération, les questions à réponses multiples et les plans de sondage complexes ne sont pas encore pris en charge.

## Évolution vers une version cliente

À confirmer avec Sodebo : fichiers exacts fournis par les instituts, nature des variables, règles des valeurs manquantes, choix de tests, pondérations éventuelles, nombre d'utilisateurs, droits et rôles, hébergement interne, politique de conservation, seuils de diffusion et critères d'acceptation. Déploiement de production : HTTPS, cookies `Secure`, authentification/SSO, gestion des autorisations, base de données chiffrée, traçabilité, tests de sécurité et validation juridique RGPD.

## Références publiques (vérifiées en novembre 2026)

- Sodebo, métiers Études : https://www.sodebo.com/recrutement/nos-metiers/developpement-produit
- CCMP, étude de cas pédagogique « Sodebo : analyse des résultats d'enquête » : https://ccmp.fr/collection-ccmp/cas-sodebo (mention de Sphinx **dans le cas académique seulement**)
- Documentation Shiny pour Python : https://shiny.posit.co/py/docs/bookmarking.html