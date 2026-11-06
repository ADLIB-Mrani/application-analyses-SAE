from fastapi.testclient import TestClient
from app.main import app, SESSIONS
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def client():
    SESSIONS.clear()
    return TestClient(app)

def test_demo_to_statistics_to_csv():
    with client() as c:
        assert c.get('/health').json()['status']=='ok'
        assert c.get('/api/status').json()['loaded'] is False
        assert c.post('/api/demo').status_code==200
        assert c.get('/api/status').json()['report']['valid']==434
        r=c.post('/api/analyze',json={'x':'age','y':'intention_achat'})
        assert r.status_code==200 and r.json()['blocked'] is False
        csv=c.post('/api/export/csv',json={'x':'age','y':'intention_achat'})
        assert csv.status_code==200 and 'text/csv' in csv.headers['content-type']
        assert 'id_repondant' not in csv.text

def test_full_workflow_group_target_session():
    with client() as c:
        c.post('/api/demo')
        groups={'age':{'Jeunes':['18-24','25-34']}}
        assert c.put('/api/groups',json={'groups':groups}).status_code==200
        targets=[{'name':'Intéressés','combine':'AND','conditions':[{'variable':'intention_achat','values':['Oui']}]}]
        assert c.put('/api/targets',json={'targets':targets}).status_code==200
        r=c.post('/api/analyze',json={'x':'age','y':'produit_prefere','target':'Intéressés'})
        assert r.status_code==200
        config=c.get('/api/session/export')
        assert config.status_code==200 and b'reponses' not in config.content
        c.put('/api/groups',json={'groups':{}})
        c.put('/api/targets',json={'targets':[]})
        reloaded=c.post('/api/session/import',files={'config':('config.json',config.content,'application/json')})
        assert reloaded.status_code==200
        assert c.get('/api/status').json()['groups']==groups
        assert c.get('/api/status').json()['targets']==targets

def test_mismatch_session_rejected():
    with client() as c:
        c.post('/api/demo')
        res=c.post('/api/session/import',files={'config':('config.json',b'{"version":1,"fingerprint":"bad"}','application/json')})
        assert res.status_code==422

def test_upload_and_bad_data():
    with client() as c:
        p=ROOT/'examples/reponses_demo.csv'
        s=ROOT/'examples/questions_demo.json'
        res=c.post('/api/upload', files={'responses':('reponses.csv',p.read_bytes(),'text/csv'), 'structure':('questions.json',s.read_bytes(),'application/json')})
        assert res.status_code==200
        bad=c.post('/api/upload',files={'responses':('malicious.exe',b'hi','application/octet-stream')})
        assert bad.status_code==422
        assert c.get('/api/status').json()['loaded'] is True

def test_sessions_are_isolated():
    with client() as first:
        first.post('/api/demo')
        with TestClient(app) as second:
            assert second.get('/api/status').json()['loaded'] is False

def test_encrypted_project_export_import_and_bad_password():
    with client() as c:
        c.post('/api/demo')
        saved=c.post('/api/archive/export',json={'passphrase':'ma phrase longue et secrete'})
        assert saved.status_code==200 and saved.content.startswith(b'SAE1')
        assert b'R0001' not in saved.content
        err=c.post('/api/archive/import',files={'archive':('project.sae',saved.content,'application/octet-stream')},
                   data={'passphrase':'un mauvais mot de passe'})
        assert err.status_code==422
        with TestClient(app) as blank:
            assert not blank.get('/api/status').json()['loaded']
            ok=blank.post('/api/archive/import',files={'archive':('project.sae',saved.content,'application/octet-stream')},
                         data={'passphrase':'ma phrase longue et secrete'})
            assert ok.status_code==200
            assert blank.get('/api/status').json()['report']['valid']==434

def test_encrypted_project_rejects_weak_passphrase():
    with client() as c:
        c.post('/api/demo')
        assert c.post('/api/archive/export',json={'passphrase':'1234'}).status_code==422