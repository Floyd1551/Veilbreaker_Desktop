"""Explicit USB-only ADB transport for armed foreground companion sessions."""
import copy
import http.client
import json
import re
import subprocess
import time
import uuid
from .android_capture import validate_capture, MAX_BYTES


def adb(path, *args):
    result = subprocess.run([path, *args], capture_output=True, text=True, timeout=10,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('ADB command failed; check the selected device and USB authorization.')
    return result.stdout.strip()


def list_devices(path):
    devices = []
    for line in adb(path, 'devices', '-l').splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and any(p.startswith('usb:') for p in parts[2:]):
            if re.fullmatch(r'[A-Za-z0-9_-]{1,128}', parts[0]):
                devices.append({'serial': parts[0], 'state': parts[1]})
    return devices


def validate_response(body, request_id, session_id=None):
    if not isinstance(body, dict) or body.get('protocol') != 1 or body.get('request_id') != request_id:
        raise ValueError('Invalid or stale companion response')
    if not isinstance(body.get('session_id'), str) or (session_id is not None and body['session_id'] != session_id):
        raise ValueError('Companion session changed')
    if body.get('status') not in {'armed', 'collecting', 'complete', 'partial', 'cancelled', 'failed'}:
        raise ValueError('Invalid companion status')
    if body.get('capture') is not None:
        validate_capture(body['capture'])
    return body


def request(port, token, command, session_id=None, **fields):
    request_id = str(uuid.uuid4())
    payload = json.dumps(dict(request_id=request_id, session_id=session_id, **fields)).encode()
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.request('POST', '/' + command, payload,
                           {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(MAX_BYTES + 1)
        if response.status != 200 or len(raw) > MAX_BYTES:
            raise ValueError('Companion rejected request; verify arming token and foreground state.')
        return validate_response(json.loads(raw), request_id, session_id)
    finally:
        connection.close()


def collect_session(adb_path, serial, token, duration_s, cancelled=lambda: False, progress=None, checkpoint=None):
    if type(duration_s) is not int or not 5 <= duration_s <= 300:
        raise ValueError('USB session duration must be 5–300 seconds')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', serial or '') or not re.fullmatch(r'[a-f0-9]{32}', token or ''):
        raise ValueError('Select a USB device and enter the current 32-character phone token')
    if {'serial': serial, 'state': 'device'} not in list_devices(adb_path):
        raise ValueError('Selected authorized USB device is unavailable')
    allocated = adb(adb_path, '-s', serial, 'forward', 'tcp:0', 'tcp:8765')
    if not allocated.isdigit() or not 1 <= int(allocated) <= 65535:
        raise ValueError('ADB did not allocate a valid forwarding port')
    port = int(allocated)
    latest = None
    session = None
    outcome = 'partial'
    try:
        response = request(port, token, 'start', duration_s=duration_s)
        session = response['session_id']
        deadline = time.monotonic() + duration_s
        next_sample = 0
        while True:
            if response.get('capture'):
                latest = response['capture']
                if checkpoint: checkpoint(latest)
            if response['status'] in {'complete', 'partial', 'cancelled', 'failed'}:
                outcome = response['status']; break
            if cancelled():
                outcome = 'cancelled'; break
            if time.monotonic() >= deadline:
                outcome = 'complete'; break
            if time.monotonic() >= next_sample and not response.get('pending', False):
                response = request(port, token, 'sample', session)
                next_sample = time.monotonic() + 5
            else:
                time.sleep(.25)
                response = request(port, token, 'status', session)
        response = request(port, token, 'stop', session, outcome=outcome)
        if response.get('capture'): latest = response['capture']
        outcome = response['status']
    except (OSError, ValueError, http.client.HTTPException):
        if latest is None: raise ValueError('No phone observations received. Check USB connection, token, permissions and companion foreground state.') from None
        outcome = 'partial'
    finally:
        if session:
            try: request(port, token, 'stop', session, outcome=outcome)
            except Exception: pass
        try: adb(adb_path, '-s', serial, 'forward', '--remove', 'tcp:' + str(port))
        except Exception: pass
    if latest is None or not latest['observations']:
        raise ValueError('Phone session returned no observations')
    latest = copy.deepcopy(latest)
    latest['collection']['outcome'] = outcome
    latest['collection']['notes'].append('USB session terminal outcome: ' + outcome)
    validate_capture(latest)
    if checkpoint: checkpoint(latest)
    return latest


def summarize_session(capture):
    groups, seen = {}, set()
    repeated = unknown = 0
    for obs in capture['observations']:
        for cell in obs['cells']:
            if cell.get('registered') is not True: continue
            identity = json.dumps([obs['subscription_key'], cell['radio'], cell['identity']], sort_keys=True)
            group = groups.setdefault(identity, {'radio': cell['radio'], 'identity': cell['identity'], 'samples': 0})
            group['samples'] += 1
            age = cell.get('age_ms')
            if age is None: unknown += 1
            else:
                stamp = (identity, obs['elapsed_realtime_ms'] - age)
                if stamp in seen: repeated += 1
                seen.add(stamp)
    return {'observations': len(capture['observations']), 'registered_cells': list(groups.values()),
            'repeated_samples': repeated, 'unknown_age_samples': unknown}
