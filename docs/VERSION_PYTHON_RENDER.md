# Version Python et hébergement externe

## Exécuter localement

L'interface **Streamlit** est implémentée en Python et réutilise le moteur statistique \`app/analysis.py\`. Prérequis : Python 3.11+.

\`\`\`bash
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
\`\`\`

Par défaut, la version démarre en mode **démonstration publique** : elle ne charge que les données fictives du dossier \`examples/\`. Les fonctionnalités sont : nettoyage, regroupements, cibles multicritères, tableaux, graphiques, khi-deux/Fisher, export d'agrégats, enregistrement/restauration des réglages.

Pour activer l'import et les archives chiffrées **uniquement en environnement local ou privé protégé** :

\`\`\`bash
# Linux/macOS
SAE_ALLOW_UPLOAD=1 streamlit run streamlit_app.py
# PowerShell
$env:SAE_ALLOW_UPLOAD="1"; streamlit run streamlit_app.py
\`\`\`

⚠️ Cet indicateur n'ajoute **aucune authentification**. Ne l'activez pas sur un service public. Les microdonnées peuvent demeurer identifiantes même après suppression des colonnes sensibles. Le masquage des petites cellules n'empêche pas les inférences par requêtes successives.

## Hébergement Render

Le fichier \`render.yaml\` prépare une application web Python sur un service Render. Mode par défaut : \`SAE_ALLOW_UPLOAD=0\`. L'URL publique n'est valide qu'après déploiement confirmé. Le service ne dépend pas de Supabase pour la démonstration.

Lien de préparation : https://dashboard.render.com/blueprint/new?repo=https://github.com/ADLIB-Mrani/application-analyses-SAE

## Supabase (optionnel, non connecté par défaut)

La base Supabase n'est pas requise pour exécuter le prototype. Son intégration future pourra servir à l'authentification et aux réglages de sessions, sans stocker les réponses individuelles tant qu'une analyse RGPD n'a pas été validée. Le script \`supabase/schema_sessions.sql\` est fourni à titre de proposition, **sans application automatique à un projet existant**.
