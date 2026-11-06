"""Moteur statistique de la SAÉ Sodebo. Aucune sortie de données individuelles."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import io
import json
import math
import re
import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency, chisquare, fisher_exact

K_MIN = 10
MAX_ROWS = 100_000
MAX_COLS = 100
MAX_BYTES = 12 * 1024 * 1024
SENSITIVE = ('nom','prenom','prénom','email','e_mail','mail','telephone','téléphone','phone',
             'adresse','address','ip_address','date_naissance','birth_date','identite',
             'identité','respondent_id','id_repondant','répondant_id')

class AnalysisError(ValueError):
    pass

@dataclass
class Survey:
    frame: pd.DataFrame
    metadata: dict[str, dict]
    report: dict[str, Any]
    fingerprint: str


def _norm(v: Any) -> str:
    if pd.isna(v):
        return ''
    return str(v).strip()


def _read_table(data: bytes, filename: str) -> pd.DataFrame:
    if len(data) > MAX_BYTES:
        raise AnalysisError('Fichier trop volumineux (limite 12 Mo).')
    lower = filename.lower()
    try:
        if lower.endswith('.csv'):
            try:
                raw = data.decode('utf-8-sig')
            except UnicodeDecodeError:
                raw = data.decode('cp1252')
            df = pd.read_csv(io.StringIO(raw), sep=None, engine='python', dtype=str, keep_default_na=False)
        elif lower.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(data), dtype=str, engine='openpyxl').fillna('')
        else:
            raise AnalysisError('Format attendu : CSV ou XLSX.')
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f'Fichier illisible : {exc}') from exc
    if df.empty or not 1 <= len(df.columns) <= MAX_COLS or len(df) > MAX_ROWS:
        raise AnalysisError('Tableau vide ou taille excessive (100 000 lignes, 100 colonnes max).')
    cols = [str(c).strip() for c in df.columns]
    if len(cols) != len(set(cols)) or any(not c for c in cols):
        raise AnalysisError('Les noms de colonnes doivent être uniques et non vides.')
    df.columns = cols
    return df.astype(str).apply(lambda s: s.str.strip())


def parse_structure(blob: bytes | None, columns: list[str]) -> dict[str, dict]:
    if not blob:
        return {c: {'label': c.replace('_', ' ').capitalize(), 'type': 'categorical',
                    'required': True, 'allowed_values': [], 'identifier': False}
                for c in columns}
    if len(blob) > 200_000:
        raise AnalysisError('Structure JSON trop volumineuse.')
    try:
        obj = json.loads(blob.decode('utf-8-sig'))
    except Exception as exc:
        raise AnalysisError('Structure JSON invalide.') from exc
    if not isinstance(obj, list):
        raise AnalysisError('La structure doit être une liste JSON de questions.')
    meta = {}
    for q in obj:
        if not isinstance(q, dict) or not isinstance(q.get('id'), str):
            raise AnalysisError('Question invalide : champ id obligatoire.')
        c = q['id']
        if c not in columns or c in meta:
            raise AnalysisError(f'Question absente du CSV ou dupliquée : {c}.')
        typ = q.get('type', 'categorical')
        if typ not in ('categorical', 'ordinal', 'identifier', 'text'):
            raise AnalysisError(f'Type non pris en charge : {typ}.')
        allowed = q.get('allowed_values', [])
        if not isinstance(allowed, list) or any(not isinstance(x, (str, int, float)) for x in allowed):
            raise AnalysisError(f'Modalités invalides pour {c}.')
        meta[c] = {'label': str(q.get('label', c))[:160], 'type': typ,
                   'required': bool(q.get('required', True)),
                   'allowed_values': list(dict.fromkeys(str(v).strip() for v in allowed)),
                   'identifier': bool(q.get('identifier', False)) or typ == 'identifier'}
    if not meta:
        raise AnalysisError('La structure doit décrire au moins une question.')
    # Les colonnes non décrites sont exclues des analyses plutôt qu'utilisées implicitement.
    return meta


def _is_sensitive(name: str) -> bool:
    s = re.sub(r'[^a-z0-9_éèêàâîôûùç]', '_', name.lower())
    return any(keyword in s for keyword in SENSITIVE)


def ingest(data: bytes, filename: str, structure: bytes | None = None) -> Survey:
    import hashlib
    raw = _read_table(data, filename)
    meta = parse_structure(structure, list(raw.columns))
    keys = list(meta)
    invalid = pd.Series(False, index=raw.index)
    reasons = {}
    for col in keys:
        opts = meta[col]
        values = raw[col].map(_norm)
        missing = values.eq('') | values.str.lower().isin(['nan', 'null', 'n/a', 'nr', 'non renseigné'])
        bad = missing & opts['required']
        allowed = set(opts['allowed_values'])
        if allowed:
            bad |= (~missing) & ~values.isin(allowed)
        reasons[col] = int(bad.sum())
        invalid |= bad
    id_cols = [c for c in keys if meta[c]['identifier'] or _is_sensitive(c) and 'id' in c.lower()]
    duplicates = pd.Series(False, index=raw.index)
    if id_cols:
        identifier = id_cols[0]
        # Ne compter comme doublons que les réponses valides, et garder la première.
        duplicates = raw.loc[~invalid, identifier].duplicated(keep='first').reindex(raw.index, fill_value=False)
    removed_bad = int(invalid.sum())
    removed_dup = int(duplicates.sum())
    kept = raw.loc[~(invalid | duplicates)].copy()
    excluded = [c for c in kept.columns if c not in meta or meta[c]['identifier']
                or meta[c]['type'] in ('identifier', 'text') or _is_sensitive(c)]
    usable = [c for c in keys if c not in excluded]
    if not usable:
        raise AnalysisError('Aucune variable catégorielle exploitable après suppression des identifiants.')
    kept = kept[usable].reset_index(drop=True)
    return Survey(kept, {k: meta[k] for k in usable}, {
        'initial': int(len(raw)), 'valid': int(len(kept)), 'removed_invalid': removed_bad,
        'removed_duplicates': removed_dup,
        'errors_by_variable': {k: v for k, v in reasons.items() if v},
        'excluded_columns': sorted(set(excluded)),
        'privacy_note': 'Les identifiants et champs libres ont été écartés de la mémoire analytique. '
            'L\'anonymat complet n\'est pas garanti (croisements et requêtes successives).'
    }, hashlib.sha256(data).hexdigest())


def valid_variables(survey: Survey) -> list[dict]:
    return [{'id': c, 'label': m['label'], 'modalities': sorted(survey.frame[c].dropna().unique().tolist()),
             'type': m['type']} for c, m in survey.metadata.items()]


def validate_groups(survey: Survey, groups: dict) -> dict:
    if not isinstance(groups, dict):
        raise AnalysisError('Regroupements attendus sous forme d’objet.')
    clean = {}
    for var, named in groups.items():
        if var not in survey.metadata or not isinstance(named, dict):
            raise AnalysisError(f'Variable ou regroupement invalide : {var}.')
        used = set()
        allowed = set(survey.frame[var].unique())
        clean[var] = {}
        for label, choices in named.items():
            if not isinstance(label, str) or not label.strip() or len(label) > 80:
                raise AnalysisError('Nom de groupe invalide.')
            if not isinstance(choices, list) or not choices or not all(isinstance(v, str) for v in choices):
                raise AnalysisError('Sélection des modalités invalide.')
            if used.intersection(choices) or set(choices) - allowed:
                raise AnalysisError('Une modalité ne peut appartenir à deux groupes ou être inconnue.')
            used.update(choices)
            clean[var][label.strip()] = choices
    return clean


def transformed(survey: Survey, groups: dict) -> pd.DataFrame:
    validated = validate_groups(survey, groups)
    df = survey.frame.copy()
    for var, named in validated.items():
        reverse = {v: label for label, vals in named.items() for v in vals}
        df[var] = df[var].map(lambda v: reverse.get(v, v))
    return df


def validate_targets(df: pd.DataFrame, targets: list[dict]) -> list[dict]:
    if not isinstance(targets, list) or len(targets) > 20:
        raise AnalysisError('Cibles invalides (maximum 20).')
    seen = set()
    out = []
    for t in targets:
        name = t.get('name') if isinstance(t, dict) else None
        conditions = t.get('conditions', []) if isinstance(t, dict) else None
        combine = t.get('combine', 'AND') if isinstance(t, dict) else None
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or name in seen:
            raise AnalysisError('Nom de cible invalide ou déjà présent.')
        if combine not in ('AND', 'OR') or not isinstance(conditions, list) or not 1 <= len(conditions) <= 8:
            raise AnalysisError('Conditions de cible invalides.')
        for c in conditions:
            if not isinstance(c, dict) or c.get('variable') not in df.columns:
                raise AnalysisError('Variable de cible invalide.')
            vals = c.get('values')
            if not isinstance(vals, list) or not vals or not all(isinstance(v, str) for v in vals):
                raise AnalysisError('Modalités de cible invalides.')
            if set(vals) - set(df[c['variable']].unique()):
                raise AnalysisError('Modalité de cible inconnue (regroupement modifié ?).')
        seen.add(name)
        out.append(t)
    return out


def target_mask(df: pd.DataFrame, t: dict | None) -> pd.Series:
    if t is None:
        return pd.Series(True, index=df.index)
    parts = [df[c['variable']].isin(c['values']) for c in t['conditions']]
    result = parts[0].copy()
    for part in parts[1:]:
        result = (result & part) if t.get('combine', 'AND') == 'AND' else (result | part)
    return result


def _safe_num(n: float | int) -> float | int | None:
    return float(n) if isinstance(n, (float, np.floating)) and math.isfinite(float(n)) else (int(n) if isinstance(n, (int, np.integer)) else None)


def _test_independence(table: pd.DataFrame, alpha: float) -> dict:
    # Retirer uniquement les marges nulles, en évitant de fausser les tests.
    t = table.loc[table.sum(axis=1) > 0, table.sum(axis=0) > 0]
    if t.shape[0] < 2 or t.shape[1] < 2:
        return {'name': 'Indépendance', 'status': 'not_applicable',
                'message': 'Au moins deux modalités par variable sont nécessaires.'}
    stat, p, ddl, expected = chi2_contingency(t.to_numpy(), correction=False)
    n = int(t.to_numpy().sum())
    v = math.sqrt(float(stat)/(n*min(t.shape[0]-1,t.shape[1]-1))) if n else None
    weak = bool((expected < 5).any())
    if t.shape == (2,2) and weak:
        odds, p_fisher = fisher_exact(t.to_numpy())
        return {'name': 'Test exact de Fisher (2×2)', 'status': 'ok', 'p_value': float(p_fisher),
                'chi2': float(stat), 'df': int(ddl), 'cramers_v': float(v), 'min_expected': float(expected.min()),
                'significant': bool(p_fisher < alpha), 'alpha': alpha,
                'message': 'Effectifs attendus faibles : p-valeur du test exact de Fisher ; χ² et V affichés à titre descriptif.'}
    return {'name': 'Khi-deux d’indépendance', 'status': 'caution' if weak else 'ok',
            'p_value': float(p), 'chi2': float(stat), 'df': int(ddl),
            'cramers_v': float(v), 'min_expected': float(expected.min()),
            'significant': bool(p < alpha) if not weak else None, 'alpha': alpha,
            'message': 'Certains effectifs théoriques sont inférieurs à 5 : résultat non interprétable sans méthode adaptée.'
            if weak else 'H₀ : indépendance des deux variables ; V de Cramér mesure l’intensité de l’association.'}


def analyze(survey: Survey, groups: dict, targets: list[dict], x: str,
            y: str | None = None, target: str | None = None, alpha: float = 0.05) -> dict:
    if not isinstance(alpha, (int, float)) or not 0 < alpha < 1:
        raise AnalysisError('Le seuil alpha doit être compris entre 0 et 1.')
    df = transformed(survey, groups)
    target_list = validate_targets(df, targets)
    if x not in df.columns or y is not None and (y not in df.columns or x == y):
        raise AnalysisError('Variables d’analyse inconnues ou identiques.')
    named = {t['name']: t for t in target_list}
    if target is not None and target not in named:
        raise AnalysisError('Cible introuvable.')
    selection = target_mask(df, named.get(target))
    sample = df.loc[selection]
    if len(sample) < K_MIN:
        return {'blocked': True, 'message': f'Analyse masquée : cible de moins de {K_MIN} répondants.',
                'n': None, 'k_min': K_MIN}
    if y is not None:
        table = pd.crosstab(sample[x], sample[y], dropna=False)
        mode = 'cross'
        stats = _test_independence(table, alpha)
        test_hypothesis = f'H₀ : {x} et {y} sont indépendantes dans la population analysée.'
    elif target is not None:
        # Comparaison de la cible à son complément, et non pas à elle-même.
        indicator = pd.Series(np.where(selection, 'Cible', 'Hors cible'), index=df.index)
        table = pd.crosstab(df[x], indicator, dropna=False)
        mode = 'target'
        stats = _test_independence(table, alpha)
        test_hypothesis = f'H₀ : la répartition de {x} est identique dans et hors de la cible.'
    else:
        counts = sample[x].value_counts().sort_index()
        table = pd.DataFrame({'Effectif': counts})
        mode = 'distribution'
        if len(counts) < 2:
            stats = {'name': 'Adéquation', 'status': 'not_applicable',
                     'message': 'Au moins deux modalités sont nécessaires.'}
        else:
            chi, p = chisquare(counts.to_numpy())
            stats = {'name': 'Khi-deux d’adéquation (répartition uniforme)', 'status': 'caution',
                     'chi2': float(chi), 'p_value': float(p), 'df': len(counts)-1,
                     'significant': None, 'alpha': float(alpha),
                     'message': 'H₀ : toutes les modalités sont équiprobables. Hypothèse technique, à valider par le métier ; ne pas interpréter comme une différence entre groupes.'}
        test_hypothesis = f'H₀ technique : les modalités de {x} ont la même probabilité.'
    arr = table.to_numpy()
    # Suppression de l'intégralité d'une sortie contenant une cellule 1..(K_MIN-1)
    # pour empêcher la reconstruction depuis les marges et graphiques associés.
    if ((arr > 0) & (arr < K_MIN)).any():
        return {'blocked': True, 'message': f'Tableau et graphique masqués : au moins une cellule comporte 1 à {K_MIN-1} individus.',
                'n': None, 'k_min': K_MIN}
    rows = [str(r) for r in table.index]
    cols = [str(c) for c in table.columns]
    vals = table.to_numpy().astype(int).tolist()
    percentages = [[round(100*v/s, 1) if s else 0 for v in r] for r, s in zip(vals, map(sum, vals))]
    return {'blocked': False, 'n': int(len(sample)), 'mode': mode, 'x': x, 'y': y,
            'target': target, 'rows': rows, 'columns': cols, 'counts': vals,
            'percentages_by_row': percentages, 'test': stats, 'hypothesis': test_hypothesis,
            'privacy': f'Seuil minimal de diffusion : {K_MIN} observations par cellule non nulle.',
            'interpretation_warning': 'Les p-valeurs ne prouvent pas une causalité. Vérifier le plan de sondage, la pondération et la multiplicité des tests.'}


def aggregate_csv(result: dict) -> bytes:
    if result.get('blocked'):
        raise AnalysisError('Export interdit : analyse masquée.')
    out = io.StringIO()
    import csv
    w = csv.writer(out, delimiter=';')
    safe = lambda s: "'"+str(s) if str(s).startswith(('=', '+', '-', '@', '\t', '\r')) else str(s)
    w.writerow(['Modalité'] + [safe(c) for c in result['columns']])
    for label, vals in zip(result['rows'], result['counts']):
        # Empêche l'injection de formules à l'ouverture Excel.
        w.writerow([safe(label)] + vals)
    return out.getvalue().encode('utf-8-sig')