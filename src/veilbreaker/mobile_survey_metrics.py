"""Conservative per-observation associations for phone survey evidence.

These are reported measurements with a nearby receiver fix, not a propagation
model or a tower location. Never spread one observation's value to other fixes.
"""
import math

from .android_capture import validate_capture
from .location_report import qualify_location

# The current collector computes both ages against one monotonic receipt time.
# Version metadata is self-reported, not cryptographic proof of its origin.
_SHARED_RECEIPT_VERSIONS = frozenset({'0.8.25-dev'})
_MAX_AGE_MS = 10_000
_MAX_OFFSET_MS = 2_000
_SIGNALS = {
    'LTE': {'rsrp': 'phone_lte_rsrp', 'rsrq': 'phone_lte_rsrq', 'rssi': 'phone_lte_rssi'},
    'NR': {'ss_rsrp': 'phone_nr_rsrp', 'ss_rsrq': 'phone_nr_rsrq', 'ss_sinr': 'phone_nr_sinr'},
}


def aligned_mobile_metrics(capture):
    """Return values keyed by exact observation ID; skip ambiguous evidence.

    Both age fields must refer to the same monotonic receipt. A cell and fix
    within two seconds are close in time, but movement can still separate them.
    """
    validate_capture(capture)
    if capture['device']['companion_version'] not in _SHARED_RECEIPT_VERSIONS:
        return {}
    seen = set()
    result = {}
    for observation in capture['observations']:
        location = observation.get('location') or {}
        cells = [cell for cell in observation['cells'] if cell.get('registered') is True]
        if (observation['outcome'] not in ('complete', 'partial') or len(cells) != 1 or
            location.get('source') != 'phone' or location.get('mock') is not False or
            not qualify_location(location)['qualified']):
            continue
        cell = cells[0]
        if cell['radio'] not in _SIGNALS or cell['connection_status'] not in ('primary', 'none'):
            continue
        age = cell.get('age_ms')
        fix_age = location.get('fix_age_ms')
        if (type(age) not in (int, float) or not math.isfinite(age) or not 0 <= age <= _MAX_AGE_MS or
            type(fix_age) not in (int, float) or not math.isfinite(fix_age) or not 0 <= fix_age <= _MAX_AGE_MS or
            abs(age - fix_age) > _MAX_OFFSET_MS):
            continue
        stamp = (observation['subscription_key'], cell['radio'], observation['elapsed_realtime_ms'] - age)
        if stamp in seen:
            continue
        seen.add(stamp)
        identity = {key: cell['identity'][key] for key in ('mcc', 'mnc', 'tac', 'cell_id', 'pci', 'earfcn', 'nrarfcn')
                    if cell['identity'].get(key) is not None}
        context = {'sources': ['android_import'], 'observation_id': observation['observation_id'],
                   'received_utc': observation['received_utc'], 'age_ms': age, 'fix_age_ms': fix_age,
                   'location_after_modem_ms': age - fix_age, 'cell_identity': identity,
                   'radio': cell['radio'], 'subscription': observation['subscription_key'],
                   'companion_version': capture['device']['companion_version'],
                   'limitation': 'Receiver fix and modem sample may differ in time and position; timestamps and device version are reported by the source.'}
        metrics = {}
        for signal, key in _SIGNALS[cell['radio']].items():
            quantity = cell['signal'].get(signal, {})
            value = quantity.get('value') if isinstance(quantity, dict) else None
            if type(value) in (int, float) and math.isfinite(value):
                metrics[key] = value
        if metrics:
            result[observation['observation_id']] = dict(metrics=metrics, context={key: dict(context) for key in metrics})
    return result
