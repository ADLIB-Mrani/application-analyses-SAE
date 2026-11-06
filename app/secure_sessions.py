"""Archive locale chiffrée des données déjà nettoyées : ne vaut pas une conformité RGPD."""
from __future__ import annotations
from dataclasses import asdict
import json
import os
import zlib
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.exceptions import InvalidTag
from .analysis import Survey, AnalysisError, validate_groups, transformed, validate_targets

MAGIC = b'SAE1'
AAD = b'SAE_SODEBO_ARCHIVE_V1'
MAX_ENCRYPTED_BYTES = 18 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 30 * 1024 * 1024

def _key(secret: str, salt: bytes) -> bytes:
    if not isinstance(secret, str) or len(secret) < 12:
        raise AnalysisError('Choisissez une phrase secrète d’au moins 12 caractères.')
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(secret.encode('utf-8'))

def encrypt_project(survey: Survey, groups: dict, targets: list[dict], secret: str) -> bytes:
    groups = validate_groups(survey,groups)
    targets = validate_targets(transformed(survey,groups),targets)
    obj = {'version': 1, 'survey': {'frame':survey.frame.to_dict(orient='records'),
           'metadata': survey.metadata, 'report':survey.report, 'fingerprint':survey.fingerprint},
           'groups':groups,'targets':targets}
    raw = json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    if len(raw) > MAX_DECOMPRESSED_BYTES:
        raise AnalysisError('Jeu trop volumineux pour une archive locale.')
    salt=os.urandom(16);nonce=os.urandom(12)
    key=_key(secret,salt)
    blob=MAGIC+salt+nonce+AESGCM(key).encrypt(nonce,zlib.compress(raw,level=6),AAD)
    if len(blob)>MAX_ENCRYPTED_BYTES:
        raise AnalysisError('Archive chiffrée trop volumineuse.')
    return blob

def decrypt_project(blob: bytes, secret: str) -> tuple[Survey,dict,list]:
    if len(blob)>MAX_ENCRYPTED_BYTES or len(blob)<49 or not blob.startswith(MAGIC):
        raise AnalysisError('Format d’archive chiffrée non reconnu.')
    salt=blob[4:20];nonce=blob[20:32];encrypted=blob[32:]
    key=_key(secret,salt)
    try:
        compressed=AESGCM(key).decrypt(nonce,encrypted,AAD)
    except InvalidTag as exc:
        raise AnalysisError('Phrase secrète erronée ou fichier chiffré altéré.') from exc
    try:
        d=zlib.decompressobj()
        raw=d.decompress(compressed,MAX_DECOMPRESSED_BYTES+1)
        if d.unconsumed_tail or len(raw)>MAX_DECOMPRESSED_BYTES or not d.eof:
            raise AnalysisError('Archive décompressée trop volumineuse ou incomplète.')
        obj=json.loads(raw)
        assert obj['version']==1
        dct=obj['survey']
        records=dct['frame']
        assert isinstance(records,list) and len(records)<=100_000
        frame=pd.DataFrame(records)
        assert len(frame.columns)<=100 and len(frame)>0
        metadata=dct['metadata']
        assert isinstance(metadata,dict) and set(frame.columns)==set(metadata)
        assert all(isinstance(c,str) and not c.startswith('__') for c in frame.columns)
        # Le format ne doit pas contenir d'identifiants directs au sens du moteur.
        from .analysis import _is_sensitive
        assert all(not _is_sensitive(c) and metadata[c]['type'] not in ('identifier','text') for c in frame.columns)
        frame=frame[list(metadata)].fillna('').astype(str)
        survey=Survey(frame,metadata,dct['report'],dct['fingerprint'])
        groups=validate_groups(survey,obj.get('groups',{}))
        targets=validate_targets(transformed(survey,groups),obj.get('targets',[]))
        return survey,groups,targets
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError('Archive chiffrée mal formée.') from exc