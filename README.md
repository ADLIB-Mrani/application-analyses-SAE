# SAÉ 5.01 / 6.01 — Application d'analyse de sondages

Prototype pédagogique d'outil décisionnel de traitement de réponses de sondages, sans affiliation officielle à Sodebo.

- Version Python/FastAPI : application complète et moteur SciPy.
- Version GitHub Pages : démonstration statique 100 % navigateur, sans transfert des fichiers de réponses.

⚠️ Ne jamais ajouter de données personnelles ou de vrais questionnaires au dépôt public. La démonstration n'est pas destinée à un usage en production.

Voir la documentation dans `docs/` et les instructions de démarrage ci-dessous.

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
python -m pytest -q
```
