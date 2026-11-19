"""Immutable, local cell-reference snapshots. No network lookups."""
from contextlib import closing
import csv
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import stat
import uuid
from pathlib import Path
from .recovery import atomic_json
from .core import utcnow_iso

MAX_BYTES=8*1024**3
MAX_ROWS=20_000_000
MAX_LINE=65536
MAX_DATABASE_BYTES=32*1024**3
COLUMNS=['radio','mcc','net','area','cell','unit','lon','lat','range','samples','changeable','created','updated','averageSignal']


class _ReferenceVerificationCancelled(ValueError):
    pass


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


def _link_or_reparse(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _reference_paths(root, dataset_id):
    if not isinstance(dataset_id, str) or not re.fullmatch(r'[a-f0-9]{32}', dataset_id):
        raise ValueError('Invalid reference identifier.')
    root = Path(root).resolve()
    folder = root / dataset_id
    manifest = folder / 'manifest.json'
    database = folder / 'cells.sqlite'
    if any(_link_or_reparse(path) for path in (folder, manifest, database)):
        raise ValueError('Reference storage contains an unsafe link.')
    if folder.resolve().parent != root:
        raise ValueError('Invalid reference path.')
    return folder, manifest, database


def _signature(info):
    return dict(size=info.st_size, mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns,
                device=info.st_dev, inode=info.st_ino)


def _same_file(path_signature, handle_signature):
    # On Windows stat() and fstat() can report different ctime semantics.
    return all(path_signature[key] == handle_signature[key]
               for key in ('size', 'mtime_ns', 'device', 'inode'))


def reference_database_signature(root, dataset_id):
    """Return a bounded database file signature without implying hash verification."""
    folder, _, database = _reference_paths(root, dataset_id)
    for suffix in ('-wal', '-shm', '-journal'):
        sidecar = folder / ('cells.sqlite' + suffix)
        if sidecar.exists() or _link_or_reparse(sidecar):
            raise ValueError('Reference database has an unverified SQLite sidecar.')
    if not database.is_file():
        raise ValueError('Reference database is missing.')
    info = database.stat()
    if not 0 < info.st_size <= MAX_DATABASE_BYTES:
        raise ValueError('Reference database size is invalid.')
    return _signature(info)


def verify_reference_database(root, dataset_id=None, cancelled=lambda: False):
    """Verify installed SQLite bytes against their recorded digest without mutation.

    Older manifests have only a source-file digest; these remain explicitly
    unverified and are never silently assigned a new database digest.
    """
    if not callable(cancelled):
        raise ValueError('Invalid cancellation callback.')
    def check():
        if cancelled():
            raise _ReferenceVerificationCancelled('Cell reference verification cancelled.')
    def result(status, detail, **values):
        return dict(status=status, detail=detail, dataset_id=dataset_id,
                    expected_sha256=values.get('expected_sha256'), actual_sha256=values.get('actual_sha256'),
                    bytes=values.get('bytes'), file_signature=values.get('file_signature'), checked_utc=utcnow_iso())
    check()
    if dataset_id is None:
        active = Path(root) / 'active.json'
        try:
            if _link_or_reparse(active):
                raise ValueError('Unsafe active-reference metadata.')
            if not active.exists():
                return result('no_active_reference', 'No active cell reference.')
            dataset_id = _json(active).get('dataset_id')
        except (OSError, ValueError, TypeError, AttributeError):
            return result('invalid', 'Active cell-reference metadata is invalid.')
        if dataset_id is None:
            return result('no_active_reference', 'No active cell reference.')
    try:
        _, manifest_path, database = _reference_paths(root, dataset_id)
        if not database.exists():
            return result('missing', 'Cell reference database is missing.')
        before = reference_database_signature(root, dataset_id)
        manifest_before = _json(manifest_path)
        if not isinstance(manifest_before, dict) or manifest_before.get('dataset_id') != dataset_id:
            return result('invalid', 'Cell reference manifest identity is invalid.')
        expected = manifest_before.get('database_sha256')
        expected_size = manifest_before.get('database_bytes')
        if expected is None and expected_size is None:
            return result('legacy_unverified', 'Legacy reference has no recorded database checksum.', bytes=before['size'])
        if (not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected)
                or type(expected_size) is not int or not 0 < expected_size <= MAX_DATABASE_BYTES):
            return result('invalid', 'Recorded database checksum or size is invalid.')
        if before['size'] != expected_size:
            return result('changed', 'Cell reference database size differs from its manifest.',
                          expected_sha256=expected, bytes=before['size'])
        digest = hashlib.sha256()
        with database.open('rb') as stream:
            handle_before = _signature(os.fstat(stream.fileno()))
            if not _same_file(before, handle_before):
                return result('changed', 'Cell reference changed before verification.', expected_sha256=expected)
            while chunk := stream.read(1024 * 1024):
                check()
                digest.update(chunk)
            after_handle = _signature(os.fstat(stream.fileno()))
        check()
        after = reference_database_signature(root, dataset_id)
        if after != before or after_handle != handle_before or _json(manifest_path) != manifest_before:
            return result('changed', 'Cell reference changed during verification.', expected_sha256=expected)
        actual = digest.hexdigest()
        return result('verified' if actual == expected else 'changed',
                      'Database SHA-256 matches the installed manifest.' if actual == expected else 'Database SHA-256 differs from the installed manifest.',
                      expected_sha256=expected, actual_sha256=actual, bytes=before['size'], file_signature=before)
    except _ReferenceVerificationCancelled:
        raise
    except FileNotFoundError:
        return result('missing', 'Cell reference files are missing.')
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return result('invalid', 'Cell reference cannot be verified: ' + str(exc))


def activate_reference(root,dataset_id):
    if dataset_id is None:
        atomic_json(Path(root)/'active.json',{'dataset_id':None})
        return
    folder=_folder(root,dataset_id)
    manifest=_json(folder/'manifest.json')
    if manifest.get('dataset_id')!=dataset_id or not (folder/'cells.sqlite').is_file():
        raise ValueError('Reference snapshot is incomplete.')
    atomic_json(Path(root)/'active.json',{'dataset_id':dataset_id})


def lookup_reference(root,key,dataset_id=None):
    manifest=_json(_folder(root,dataset_id)/"manifest.json") if dataset_id else active_reference(root)
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
            check()
            if verify_reference_database(root, entry['dataset_id'], cancelled)['status'] == 'verified':
                return entry
    dataset_id=uuid.uuid4().hex; folder=_folder(root,dataset_id)
    folder.mkdir()
    accepted=rejected=unsupported=count=0
    bounds=None; radio_counts={}; mccs=set()
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
                    if len(header)>MAX_LINE: raise ValueError('Invalid OpenCellID full-export first row.')
                    first=next(csv.reader([header.decode('utf-8-sig').strip()]))
                    if first!=COLUMNS:
                        # Country exports may omit the heading; require the exact 14-column
                        # schema and an integer MCC before treating the line as data.
                        if len(first)!=len(COLUMNS) or first[0] not in ('LTE','NR','GSM','UMTS','CDMA') or not re.fullmatch(r'[0-9]{3}',first[1]):
                            raise ValueError('Invalid OpenCellID full-export header or first row.')
                        yield dict(zip(COLUMNS,first),mnc=first[2],tac=first[3],cell_id=first[4],
                                   source='OpenCellID',verification='estimated cell location')
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
            if isinstance(row,dict) and row.get('radio') not in ('LTE','NR'):
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
            lon,lat=payload['lon'],payload['lat']
            bounds=[lon,lat,lon,lat] if bounds is None else [min(bounds[0],lon),min(bounds[1],lat),max(bounds[2],lon),max(bounds[3],lat)]
            radio_counts[key[0]]=radio_counts.get(key[0],0)+1
            mccs.add(key[1])
        if not accepted: raise ValueError('No supported valid reference records were found.')
        check()
        db.execute('CREATE INDEX identity_lookup ON cells(radio,mcc,mnc,tac,cell_id)')
        db.commit();db.close();db=None
        database_path=folder/'cells.sqlite'
        database_digest=hashlib.sha256();database_bytes=0
        before=reference_database_signature(root,dataset_id)
        with database_path.open('rb') as stream:
            handle_before=_signature(os.fstat(stream.fileno()))
            if not _same_file(before,handle_before): raise ValueError('Reference database changed before hashing.')
            while chunk:=stream.read(1024*1024):
                check();database_bytes+=len(chunk)
                if database_bytes>MAX_DATABASE_BYTES: raise ValueError('Reference database exceeds size limit.')
                database_digest.update(chunk)
            after_handle=_signature(os.fstat(stream.fileno()))
        if not database_bytes: raise ValueError('Reference database is empty.')
        if after_handle!=handle_before or reference_database_signature(root,dataset_id)!=before or database_bytes!=before['size']:
            raise ValueError('Reference database changed during hashing.')
        manifest=dict(schema_version=1,adapter_version=1,dataset_id=dataset_id,sha256=sha,
                      database_sha256=database_digest.hexdigest(),database_bytes=database_bytes,
                      imported_utc=utcnow_iso(),accepted=accepted,rejected=rejected,unsupported=unsupported,
                      source=metadata['source'],license=metadata['license'],date=metadata['date'],
                      coverage=dict(bounds=bounds,radio_counts=radio_counts,mccs=sorted(mccs),
                                    note='Bounds describe observed records, not complete coverage.'),
                      format='operator' if operator else 'opencellid',
                      attribution='OpenCellID — https://opencellid.org — CC BY-SA 4.0 — https://creativecommons.org/licenses/by-sa/4.0/ — converted to SQLite; unsupported and invalid records excluded' if not operator else metadata['source'])
        check();atomic_json(folder/'manifest.json',manifest)
        return manifest
    except Exception:
        if db is not None: db.close()
        # Only this newly created UUID staging directory is removed.
        shutil.rmtree(folder)
        raise
