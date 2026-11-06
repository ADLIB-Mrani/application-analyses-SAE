# Format d'entrée — contrat d'importation v0.1

## Fichier réponses

CSV (encodage UTF-8 ou Windows-1252, séparateur `;`, `,` ou tabulation reconnu automatiquement) ou XLSX. Une ligne correspond à une personne interrogée et chaque colonne à un identifiant de question (par exemple `age`, `region`, `frequence_achat`). Première ligne = noms de colonnes. Valeurs nominales stockées sous forme de chaînes. Pas plus de 100 000 lignes, 100 colonnes et 12 Mo. Seule la première feuille XLSX est lue.

## Fichier questions (facultatif, JSON)

```json
[
  {"id":"id_repondant", "label":"Identifiant technique", "type":"identifier", "required":true, "allowed_values":[], "identifier":true},
  {"id":"age", "label":"Tranche d'âge", "type":"categorical", "required":true, "allowed_values":["18-24","25-34","35-49","50+"], "identifier":false}
]
```

Types reconnus : `categorical`, `ordinal`, `identifier`, `text`. Les questions non décrites dans le JSON sont exclues du périmètre d'analyse. Les colonnes explicitement identifiantes, correspondant à des noms de données personnelles (heuristique), ou de type `text`, sont exclues de la mémoire analytique. Une vérification manuelle du caractère identifiant reste indispensable.

Une réponse est rejetée si une variable `required` manque (`""`, `nan`, `null`, `n/a`, `nr`, `non renseigné`) ou si sa valeur n'appartient pas à `allowed_values` quand ce champ est renseigné. Le premier identifiant détecté sert à exclure les doublons parmi les réponses autrement valides. Le rapport affiche la quantité de lignes rejetées et le nombre d'erreurs par question ; un répondant peut produire plusieurs erreurs. Les données d'origine ne sont pas réécrites.

## Cibles

```json
{"name":"Jeunes acheteurs", "combine":"AND", "conditions":[
  {"variable":"age", "values":["18-24", "25-34"]},
  {"variable":"frequence_achat", "values":["Hebdomadaire"]}
]}
```

Les filtres portent sur les modalités **après** regroupement. Les combinaisons `AND` et `OR` sont prises en charge, avec un maximum de 8 conditions par cible et 20 cibles par session.

## Sauvegarde des paramètres

Fichier JSON versionné avec `fingerprint` SHA-256 du CSV/XLSX original, `groups` et `targets`, **sans les réponses ni les identifiants des répondants**. Pour restaurer, réimporter exactement le même fichier de réponses.

## Archive chiffrée complète `.sae`

Option distincte du JSON : une sauvegarde AES-GCM avec dérivation Scrypt contient les réponses nettoyées (hors champs identifiants écartés), les métadonnées, le rapport de nettoyage et la configuration. Phrase secrète d’au moins 12 caractères, non stockée par le serveur. Ce mode de sauvegarde conserve **des données au niveau répondant**, éventuellement réidentifiables : ne pas la transmettre sans autorisation. Relecture par le même logiciel, pas de fonction de récupération de phrase secrète.