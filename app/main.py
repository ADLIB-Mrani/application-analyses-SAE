"""Application web pédagogique : analyses agrégées uniquement, sans authentification métier."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
import secrets
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .secure_sessions import encrypt_project, decrypt_project
from .analysis import (Survey, AnalysisError, ingest, transformed, valid_variables,
                       validate_groups, validate_targets, analyze, aggregate_csv, K_MIN)

BASE = Path(__file__).resolve().parents[1]
app = FastAPI(title='SAÉ Sodebo – Analyse des enquêtes', version='0.1.0',
              docs_url=None, redoc_url=None)
app.mount('/assets', StaticFiles(directory=BASE / 'app' / 'static'), name='assets')

@dataclass
class SessionData:
    survey: Survey | None = None
    groups: dict = field(default_factory=dict)
    targets: list = field(default_factory=list)

# Démonstrateur local : états non persistants, une authentification est nécessaire avant production.
SESSIONS: dict[str, SessionData] = {}

@app.middleware('http')
async def visitor_cookie(request: Request, call_next):
    sid = request.cookies.get('sae_session')
    created = sid not in SESSIONS
    if created:
        sid = secrets.token_urlsafe(32)
        SESSIONS[sid] = SessionData()
    request.state.sid = sid
    response = await call_next(request)
    if created:
        response.set_cookie('sae_session', sid, httponly=True, samesite='strict', max_age=86400,
                            secure=False)  # HTTPS et secure=True requis en production
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'"
    return response

@app.exception_handler(AnalysisError)
async def handle_analysis_error(request: Request, exc: AnalysisError):
    return JSONResponse(status_code=422, content={'detail': str(exc)})


def state(request: Request) -> SessionData:
    return SESSIONS[request.state.sid]


def require_loaded(request: Request) -> SessionData:
    s = state(request)
    if s.survey is None:
        raise AnalysisError('Chargez d’abord un jeu de réponses (ou le jeu de démonstration).')
    return s

@app.get('/')
async def home():
    return FileResponse(BASE / 'app' / 'static' / 'index.html')

@app.get('/api/status')
async def status(request: Request):
    s = state(request)
    if s.survey is None:
        return {'loaded': False, 'k_min': K_MIN}
    df = transformed(s.survey, s.groups)
    validate_targets(df, s.targets)
    variables = valid_variables(s.survey)
    for v in variables:
        v['modalities'] = sorted(df[v['id']].unique().tolist())
    return {'loaded': True, 'report': s.survey.report, 'variables': variables,
            'groups': s.groups, 'targets': s.targets, 'k_min': K_MIN,
            'fingerprint': s.survey.fingerprint[:12]}

@app.post('/api/demo')
async def demo(request: Request):
    data = (BASE / 'examples' / 'reponses_demo.csv').read_bytes()
    schema = (BASE / 'examples' / 'questions_demo.json').read_bytes()
    s = state(request)
    s.survey = ingest(data, 'reponses_demo.csv', schema)
    s.groups = {}
    s.targets = []
    return {'message': 'Jeu synthétique chargé.', 'report': s.survey.report}

@app.post('/api/upload')
async def upload(request: Request, responses: UploadFile = File(...), structure: UploadFile | None = File(None)):
    data = await responses.read(12*1024*1024 + 1)
    meta = await structure.read(200_001) if structure else None
    survey = ingest(data, responses.filename or 'import.csv', meta)
    s = state(request)
    s.survey = survey
    s.groups = {}
    s.targets = []
    return {'message': 'Import réussi.', 'report': survey.report}

class GroupsPayload(BaseModel):
    groups: dict = Field(default_factory=dict)

@app.put('/api/groups')
async def set_groups(request: Request, payload: GroupsPayload):
    s = require_loaded(request)
    groups = validate_groups(s.survey, payload.groups)
    df = transformed(s.survey, groups)
    # Les anciennes cibles doivent rester cohérentes avec les regroupements.
    try:
        validate_targets(df, s.targets)
    except AnalysisError:
        s.targets = []
    s.groups = groups
    return {'message': 'Regroupements enregistrés.', 'targets_reset': not bool(s.targets)}

class TargetsPayload(BaseModel):
    targets: list[dict]

@app.put('/api/targets')
async def set_targets(request: Request, payload: TargetsPayload):
    s = require_loaded(request)
    df = transformed(s.survey, s.groups)
    s.targets = validate_targets(df, payload.targets)
    return {'message': 'Cibles enregistrées.', 'count': len(s.targets)}

class AnalysisPayload(BaseModel):
    x: str
    y: str | None = None
    target: str | None = None
    alpha: float = 0.05

@app.post('/api/analyze')
async def run_analysis(request: Request, payload: AnalysisPayload):
    s = require_loaded(request)
    return analyze(s.survey, s.groups, s.targets, payload.x, payload.y,
                   payload.target, payload.alpha)

@app.post('/api/export/csv')
async def export_csv(request: Request, payload: AnalysisPayload):
    s = require_loaded(request)
    result = analyze(s.survey, s.groups, s.targets, payload.x, payload.y, payload.target, payload.alpha)
    csv_data = aggregate_csv(result)
    return Response(csv_data, media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="tableau_agrege.csv"'})

@app.get('/api/session/export')
async def export_session(request: Request):
    s = require_loaded(request)
    data = json.dumps({'version': 1, 'fingerprint': s.survey.fingerprint,
                       'groups': s.groups, 'targets': s.targets}, ensure_ascii=False, indent=2)
    return Response(data, media_type='application/json; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="configuration_analyse.json"'})

@app.post('/api/session/import')
async def import_session(request: Request, config: UploadFile = File(...)):
    s = require_loaded(request)
    blob = await config.read(200_001)
    if len(blob) > 200_000:
        raise AnalysisError('Fichier de session trop volumineux.')
    try:
        obj = json.loads(blob)
    except Exception as exc:
        raise AnalysisError('Configuration JSON illisible.') from exc
    if not isinstance(obj, dict) or obj.get('version') != 1 or obj.get('fingerprint') != s.survey.fingerprint:
        raise AnalysisError('Cette configuration appartient à un autre fichier de réponses : importez ce fichier original.')
    groups = validate_groups(s.survey, obj.get('groups', {}))
    targets = validate_targets(transformed(s.survey, groups), obj.get('targets', []))
    s.groups, s.targets = groups, targets
    return {'message': 'Configuration restaurée.'}

class SecretPayload(BaseModel):
    passphrase: str

@app.post('/api/archive/export')
async def export_archive(request: Request, payload: SecretPayload):
    s=require_loaded(request)
    data=encrypt_project(s.survey,s.groups,s.targets,payload.passphrase)
    return Response(data,media_type='application/octet-stream',
                    headers={'Content-Disposition':'attachment; filename="projet_chiffre.sae"'})

@app.post('/api/archive/import')
async def import_archive(request: Request, archive: UploadFile = File(...), passphrase: str = Form(...)):
    data=await archive.read(18*1024*1024+1)
    survey,groups,targets=decrypt_project(data,passphrase)
    s=state(request)
    s.survey,s.groups,s.targets=survey,groups,targets
    return {'message':'Projet chiffré restauré, données nettoyées incluses.'}

@app.get('/health')
async def health():
    return {'status': 'ok'}