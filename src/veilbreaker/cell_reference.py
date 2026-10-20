"""Immutable, local cell-reference snapshots. No network lookups."""
from contextlib import closing
import csv
import gzip
import hashlib
import json
import math
import re
import shutil
import sqlite3
import uuid
from pathlib import Path
from .recovery import atomic_json
from .core import utcnow_iso

MAX_BYTES=8*1024**3
MAX_ROWS=20_000_000
MAX_LINE=65536
COLUMNS=['radio','mcc','net','area','cell','unit','lon','lat','range','samples','changeable','created','updated','averageSignal']


def integer(value, maximum, minimum=0):
    if type(value) is int:
        result=value
    elif isinstance(value,str) and re.fullmatch(r'[0-9]{1,16}',value):
        result=int(value)
    else: raise ValueError('Identity must contain unsigned integers.')
    if not minimum<=result<=maximum: raise ValueError('Identity or reference number is outside its valid range.')
    return result


def identity_key(row):
    radio=row.get('radio')
    if radio not in ('LTE','NR'): raise ValueError('Unsupported radio technology.')
    return (radio,integer(row.get('mcc'),999,100),integer(row.get('mnc'),999),
            integer(row.get('tac'),65535 if radio=='LTE' else 16777215),
            integer(row.get('cell_id'),268435455 if radio=='LTE' else 68719476735))


def _folder(root,dataset_id):
    if not isinstance(dataset_id,str) or not re.fullmatch('[a-f0-9]{32}',dataset_id):
        raise ValueError('Invalid reference identifier.')
    root=Path(root).resolve(); target=(root/dataset_id).resolve()
    if not target.is_relative_to(root): raise ValueError('Invalid reference path.')
    return target


def _json(path):
    if path.stat().st_size>1024*1024: raise ValueError('Reference metadata exceeds size limit.')
    return json.loads(path.read_text(encoding='utf-8'))


def list_references(root):
    root=Path(root)
    rows=[]
    if not root.exists(): return rows
    for folder in sorted(root.iterdir()):
        if not re.fullmatch('[a-f0-9]{32}',folder.name): continue
        try:
            row=_json(_folder(root,folder.name)/'manifest.json')
            if row['dataset_id']==folder.name and (folder/'cells.sqlite').is_file(): rows.append(row)
        except (OSError,ValueError,KeyError): continue
    return rows


def active_reference(root):
    path=Path(root)/'active.json'
    if not path.exists(): return None
    value=_json(path)
    if value.get('dataset_id') is None: return None
    folder=_folder(root,value['dataset_id'])
    manifest=_json(folder/'manifest.json')
    if not (folder/'cells.sqlite').is_file(): raise ValueError('Active reference database is missing.')
    return manifest


def activate_reference(root,dataset_id):
    if dataset_id is None:
        atomic_json(Path(root)/'active.json',{'dataset_id':None})
        return
    folder=_folder(root,dataset_id)
    manifest=_json(folder/'manifest.json')
    if manifest.get('dataset_id')!=dataset_id or not (folder/'cells.sqlite').is_file():
        raise ValueError('Reference snapshot is incomplete.')
    atomic_json(Path(root)/'active.json',{'dataset_id':dataset_id})


def lookup_reference(root,key):
    manifest=active_reference(root)
    if manifest is None: return []
    folder=_folder(root,manifest['dataset_id'])
    with closing(sqlite3.connect((folder/'cells.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        rows=db.execute('SELECT payload FROM cells WHERE radio=? AND mcc=? AND mnc=? AND tac=? AND cell_id=? LIMIT 201',key).fetchall()
    return [dict(json.loads(row[0]),dataset=manifest) for row in rows]


def _coordinate(value,limit):
    if isinstance(value,bool): raise ValueError('Invalid reference coordinate.')
    result=float(value)
    if not math.isfinite(result) or abs(result)>limit: raise ValueError('Invalid reference coordinate.')
    return result


def import_reference(root,source,metadata,cancelled,progress):
    root=Path(root); source=Path(source)
    for key in ('source','license','date'):
        if not isinstance(metadata.get(key),str) or not metadata[key].strip() or len(metadata[key])>500:
            raise ValueError('Supply reference source, license and date (Unknown is allowed).')
    if 'diff' in source.name.lower(): raise ValueError('Import a full snapshot, not a daily diff.')
    root.mkdir(parents=True,exist_ok=True)
    def check():
        if cancelled(): raise ValueError('Reference import cancelled.')
    digest=hashlib.sha256(); size=0
    with source.open('rb') as stream:
        while chunk:=stream.read(1024*1024):
            check();size+=len(chunk)
            if size>MAX_BYTES: raise ValueError('Reference file exceeds size limit.')
            digest.update(chunk)
    sha=digest.hexdigest()
    for entry in list_references(root):
        if entry.get('sha256')==sha and all(entry.get(k)==metadata[k] for k in ('source','license','date')):
            check(); return entry
    dataset_id=uuid.uuid4().hex; folder=_folder(root,dataset_id)
    folder.mkdir()
    accepted=rejected=unsupported=count=0
    db=None
    try:
        db=sqlite3.connect(folder/'cells.sqlite')
        db.execute('CREATE TABLE cells(radio TEXT,mcc INTEGER,mnc INTEGER,tac INTEGER,cell_id INTEGER,payload TEXT)')
        operator=source.suffix.lower()=='.json'
        if operator:
            if size>8*1024*1024: raise ValueError('Operator reference JSON exceeds 8 MiB.')
            value=json.loads(source.read_text(encoding='utf-8-sig'))
            rows=value.get('records')
            if value.get('schema_version')!=1 or not isinstance(rows,list) or len(rows)>10000:
                raise ValueError('Invalid operator reference format.')
        else:
            def records():
                opener=gzip.open if source.suffix.lower()=='.gz' else open
                total=0
                with opener(source,'rb') as stream:
                    header=stream.readline(MAX_LINE+1);total+=len(header)
                    if len(header)>MAX_LINE or next(csv.reader([header.decode('utf-8-sig').strip()]))!=COLUMNS:
                        raise ValueError('Invalid OpenCellID full-export header.')
                    while raw:=stream.readline(MAX_LINE+1):
                        check(); total+=len(raw)
                        if len(raw)>MAX_LINE or total>MAX_BYTES: raise ValueError('Reference decompressed size limit exceeded.')
                        values=next(csv.reader([raw.decode('utf-8').strip()]))
                        if len(values)!=len(COLUMNS): yield {};continue
                        row=dict(zip(COLUMNS,values))
                        row.update(mnc=row['net'],tac=row['area'],cell_id=row['cell'],
                                   source='OpenCellID',verification='estimated cell location')
                        yield row
            rows=records()
        for row in rows:
            check();count+=1
            if count>MAX_ROWS: raise ValueError('Reference record limit exceeded.')
            if count==1 or count%10000==0:
                if shutil.disk_usage(root).free<512*1024*1024: raise ValueError('Insufficient staging disk space.')
                progress({'read':count,'accepted':accepted,'rejected':rejected,'unsupported':unsupported})
            if isinstance(row,dict) and row.get('radio') not in (('LTE','NR') if operator else ('LTE',)):
                unsupported+=1;continue
            try:
                key=identity_key(row)
                payload=dict(row,lon=_coordinate(row.get('lon'),180),lat=_coordinate(row.get('lat'),90),source_row=count)
                if operator:
                    if not isinstance(row.get('source'),str) or not row['source'].strip(): raise ValueError('Missing source.')
                    if row.get('verification') not in ('operator-entered','operator-verified'): raise ValueError('Missing verification status.')
                else:
                    for field in ('range','samples','created','updated'):
                        payload[field]=integer(row.get(field),2**63-1)
                encoded=json.dumps(payload,allow_nan=False)
                if len(encoded.encode())>MAX_LINE: raise ValueError('Reference record too large.')
            except (ValueError,TypeError,AttributeError,OverflowError): rejected+=1;continue
            db.execute('INSERT INTO cells VALUES(?,?,?,?,?,?)',(*key,encoded));accepted+=1
        if not accepted: raise ValueError('No supported valid reference records were found.')
        check()
        db.execute('CREATE INDEX identity_lookup ON cells(radio,mcc,mnc,tac,cell_id)')
        db.commit();db.close();db=None
        manifest=dict(schema_version=1,adapter_version=1,dataset_id=dataset_id,sha256=sha,
                      imported_utc=utcnow_iso(),accepted=accepted,rejected=rejected,unsupported=unsupported,
                      source=metadata['source'],license=metadata['license'],date=metadata['date'],
                      format='operator' if operator else 'opencellid',
                      attribution='OpenCellID — https://opencellid.org — CC BY-SA 4.0 — https://creativecommons.org/licenses/by-sa/4.0/' if not operator else metadata['source'])
        check();atomic_json(folder/'manifest.json',manifest)
        return manifest
    except Exception:
        if db is not None: db.close()
        # Only this newly created UUID staging directory is removed.
        shutil.rmtree(folder)
        raise
