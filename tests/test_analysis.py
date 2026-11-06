from pathlib import Path
import json
import pytest
from app.analysis import ingest, analyze, AnalysisError, transformed, target_mask, aggregate_csv, K_MIN

ROOT = Path(__file__).resolve().parents[1]
DATA=(ROOT/'examples/reponses_demo.csv').read_bytes()
SCHEMA=(ROOT/'examples/questions_demo.json').read_bytes()

@pytest.fixture
def survey(): return ingest(DATA, 'reponses_demo.csv', SCHEMA)

def test_import_and_cleanup(survey):
    assert survey.report['initial'] == 440
    assert survey.report['removed_invalid'] == 5
    assert survey.report['removed_duplicates'] == 1
    assert survey.report['valid'] == 434
    assert 'id_repondant' not in survey.frame.columns
    assert survey.report['excluded_columns'] == ['id_repondant']

def test_malformed_value_excluded(survey):
    assert 'Valeur invalide' not in survey.frame.produit_prefere.unique()
    assert 'Inconnu' not in survey.frame.region.unique()

def test_groups_safely_transform(survey):
    g={'age':{'Jeunes':['18-24','25-34']}}
    tr=transformed(survey,g)
    assert 'Jeunes' in tr.age.unique()
    assert '18-24' not in tr.age.unique()
    assert '18-24' in survey.frame.age.unique()

def test_overlapping_groups_rejected(survey):
    with pytest.raises(AnalysisError):
        transformed(survey, {'age':{'Jeunes':['18-24'],'Autre':['18-24']}})

def test_target_and(survey):
    df=transformed(survey,{})
    t={'name':'test','combine':'AND','conditions':[
        {'variable':'age','values':['18-24']},
        {'variable':'intention_achat','values':['Oui']}]}
    mask=target_mask(df,t)
    assert mask.sum()>0
    assert all(df.loc[mask,'age']=='18-24')
    assert all(df.loc[mask,'intention_achat']=='Oui')

def test_crosstab_chi2_and_counts(survey):
    r=analyze(survey,{},[],'age','intention_achat')
    assert not r['blocked']
    assert sum(map(sum,r['counts']))==survey.report['valid']
    assert r['test']['name'].startswith('Khi-deux')
    assert 0 <= r['test']['p_value'] <= 1

def test_univariate_explicit_uniform_null(survey):
    r=analyze(survey,{},[],'region')
    assert not r['blocked']
    assert 'uniforme' in r['test']['name']
    assert r['test']['status']=='caution'

def test_suppression_any_small_cell(survey):
    # Sélectionner assez de personnes pour être > K_MIN, mais isoler une petite cellule.
    df=survey.frame
    subset=df[(df['age']=='18-24') & (df['region']=='Ouest')]
    # Le test analyse une cible large avec une ventilation à cellules petites (satisfaction x produit préféré).
    targets=[{'name':'petit','combine':'AND','conditions':[{'variable':'age','values':['18-24']}, {'variable':'region','values':['Ouest']}]}]
    r=analyze(survey,{},targets,'satisfaction','produit_prefere','petit')
    assert r['blocked'] is True
    assert 'counts' not in r

def test_tiny_target_suppressed(survey):
    # Impossible d'injecter de modalités inconnues.
    with pytest.raises(AnalysisError):
        analyze(survey,{},[{'name':'test','combine':'AND','conditions':[{'variable':'age','values':['inconnue']}]}], 'age',None,'test')

def test_export_without_raw_records(survey):
    r=analyze(survey,{},[],'age','intention_achat')
    export=aggregate_csv(r).decode('utf-8-sig')
    assert 'id_repondant' not in export
    assert 'R0001' not in export
    assert 'Modalité' in export

def test_excel_csv_formula_sanitized():
    r={'blocked':False,'rows':['=1+1'],'columns':['Effectif'], 'counts':[[22]]}
    assert "'=1+1" in aggregate_csv(r).decode('utf-8-sig')