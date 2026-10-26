"""Operator-entered cellular metric explanation, separate from captured evidence."""
import math

from .android_capture import SIGNALS
from .cellular_report import interpretation
from .core import DiagnosticProfile


METRICS = {
    'LTE': (('rsrp', 'RSRP', 'rsrp', 'Reference signal received power; downlink level.'),
            ('rsrq', 'RSRQ', 'rsrq', 'Reference signal quality relative to received carrier power.'),
            ('sinr', 'LTE SINR / RSSNR', 'rssnr', 'Wanted signal relative to interference and noise; modem definitions may vary.')),
    'NR': (('rsrp', 'SS-RSRP', 'ss_rsrp', 'Synchronization-signal reference power; distinct from LTE RSRP.'),
           ('rsrq', 'SS-RSRQ', 'ss_rsrq', 'Synchronization-signal quality relative to received carrier power.'),
           ('sinr', 'SS-SINR', 'ss_sinr', 'Synchronization-signal quality relative to interference and noise.')),
}


def interpret_signal(radio, inputs):
    if radio not in METRICS:
        raise ValueError('Choose LTE or NR.')
    if not isinstance(inputs, dict):
        raise ValueError('Enter a metric mapping.')
    values, rows, missing = {}, [], []
    for key, label, source_key, meaning in METRICS[radio]:
        raw = inputs.get(key)
        if raw is None or raw == '':
            values[key] = None
            missing.append(key)
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f'{label}: enter a number or leave blank.') from None
        unit, low, high = SIGNALS[source_key]
        if isinstance(raw, bool) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{label}: enter a finite value from {low:g} to {high:g} {unit}, or leave blank.')
        values[key] = value
        rows.append({'key': key, 'label': label, 'value': value, 'unit': unit,
                     'guidance': interpretation(source_key, value), 'meaning': meaning})
    if not rows:
        raise ValueError('Enter at least one exposed signal metric; leave unavailable fields blank.')

    profile = DiagnosticProfile()
    power, quality, rsrq = values['rsrp'], values['sinr'], values['rsrq']
    if power is None or quality is None:
        if rsrq is not None and rsrq <= profile.rsrq_fair:
            pattern = {'code': 'rsrq_limited_context', 'title': 'Low RSRQ with limited context',
                       'explanation': 'RSRQ is low, but the available values cannot identify whether load, interference, overlap or measurement conditions dominate.',
                       'next': 'Capture RSRP and SINR for the same cell and band, then compare repeated samples and traffic.'}
        else:
            pattern = {'code': 'insufficient_pair', 'title': 'Partial signal context',
                       'explanation': 'A power/quality relationship cannot be assessed without both reference power and SINR.',
                       'next': 'Capture the missing metric at the same cell, band, position and time if the device exposes it.'}
    elif power >= profile.rsrp_good and quality < profile.sinr_fair:
        pattern = {'code': 'strong_power_weak_quality', 'title': 'Strong power with weak quality',
                   'explanation': 'Reference power is relatively strong while SINR is low. Interference, cell overlap, load or geometry may contribute; these values alone do not identify the cause.',
                   'next': 'Compare serving and neighboring cells, band, time-of-day and spectrum/throughput at the same position.'}
    elif power <= profile.rsrp_fair and quality >= profile.sinr_good:
        pattern = {'code': 'weak_power_clean_quality', 'title': 'Weak power with comparatively clean quality',
                   'explanation': 'Reference power is low while SINR is relatively good. Path loss or penetration is worth investigating before assuming interference.',
                   'next': 'Compare indoor/outdoor placement, antenna orientation, band and cell while holding the test conditions steady.'}
    elif power <= profile.rsrp_fair and quality < profile.sinr_fair:
        pattern = {'code': 'weak_power_weak_quality', 'title': 'Weak power and weak quality',
                   'explanation': 'Both level and SINR warrant investigation; a single sample cannot separate coverage, interference and load.',
                   'next': 'Repeat at nearby positions and under traffic, tracking cell, band, RSRQ, SINR and throughput.'}
    elif rsrq is not None and rsrq <= profile.rsrq_fair and quality >= profile.sinr_good:
        pattern = {'code': 'quality_metrics_differ', 'title': 'RSRQ and SINR give different clues',
                   'explanation': 'RSRQ is low while SINR is comparatively good. Measurement bandwidth, timing, load and reference definitions can differ; no single cause follows.',
                   'next': 'Repeat both metrics for the same cell and band during idle and active traffic, checking sample age.'}
    elif rsrq is not None and rsrq <= profile.rsrq_fair and quality < profile.sinr_fair:
        pattern = {'code': 'quality_metrics_low', 'title': 'Both quality indicators are low',
                   'explanation': 'RSRQ and SINR both suggest radio quality deserves investigation, but do not identify a particular interferer or congestion source.',
                   'next': 'Compare neighbor cells, band, spectrum and time-of-day while repeating traffic measurements.'}
    else:
        pattern = {'code': 'no_specific_pattern', 'title': 'No single RF pattern from these values',
                   'explanation': 'The entered pair does not match a simple power/quality contrast. Service behavior still depends on bandwidth, load, scheduling and network path.',
                   'next': 'Correlate with throughput, latency, loss and repeated samples from the same cell and band.'}
    return {'kind': 'operator-entered interpretation', 'radio': radio, 'metrics': values,
            'rows': rows, 'missing': missing, 'pattern': pattern,
            'method': 'Broad field guidance using the default Veilbreaker diagnostic profile and cellular report labels.',
            'thresholds': {'rsrp_good_dbm': profile.rsrp_good, 'rsrp_fair_dbm': profile.rsrp_fair,
                           'rsrq_fair_db': profile.rsrq_fair,
                           'sinr_fair_db': profile.sinr_fair, 'sinr_good_db': profile.sinr_good},
            'limitations': ('Operator-entered values are not captured evidence. LTE and NR reference measurements differ; compare like metrics from the same radio and cell. '
                            'Guidance ranges are broad, not carrier/device guarantees. No serving-cell identity, interference source, throughput or site diagnosis is established.')}
