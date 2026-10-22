"""Conservative capture-local patterns, independent of desktop transport health."""
import json
import math
import statistics
from html import escape

VERSION = 'capture-patterns-1'


def finding(code, title, observation, interpretation, next_test, **evidence):
    return dict(id=code, title=title, observation=observation,
                interpretation=interpretation, next_test=next_test, evidence=evidence)


def cellular_patterns(envelope):
    from .android_capture import validate_capture
    validate_capture(envelope)
    groups, seen, previous, changes = {}, set(), {}, {}
    excluded = qualified = omitted = 0
    for obs in envelope['observations']:
        eligible = []
        for cell in obs['cells']:
            if cell.get('registered') is not True or cell['radio'] not in ('LTE', 'NR'):
                continue
            ident = cell['identity']
            # Missing identity cannot establish continuity of a serving cell.
            identity = [ident.get(k) for k in ('mcc', 'mnc', 'cell_id')]
            # Optional TAC/channel metadata can appear/disappear without a cell change.
            key = json.dumps([obs['subscription_key'], cell['radio'], identity])
            age = cell.get('age_ms')
            stamp = obs['elapsed_realtime_ms'] - age if age is not None else None
            if (age is None or age > 10000 or stamp < 0 or not all(identity)
                    or obs['outcome'] not in ('complete', 'partial')):
                excluded += 1
                continue
            if (key, stamp) in seen:
                excluded += 1
                scope = (obs['subscription_key'], cell['radio'])
                if cell['connection_status'] == 'primary' and previous.get(scope) == (key, stamp):
                    # Keep continuity without counting this callback as evidence.
                    eligible.append((cell['radio'], key, stamp))
                continue
            if key not in groups and len(groups) >= 128:
                omitted += 1
                continue
            seen.add((key, stamp))
            samples = groups.setdefault(key, [])
            if samples and stamp <= samples[-1][0]:
                excluded += 1
                continue
            samples.append((stamp, cell['signal']))
            qualified += 1
            if cell['connection_status'] == 'primary':
                eligible.append((cell['radio'], key, stamp))
        # Compare only unambiguous primary cells within the same SIM and RAT.
        for radio in ('LTE', 'NR'):
            entries = [v for v in eligible if v[0] == radio]
            scope = (obs['subscription_key'], radio)
            if len(entries) != 1:
                previous.pop(scope, None)
                continue
            _, key, stamp = entries[0]
            last = previous.get(scope)
            if last and stamp <= last[1]:
                # Another cell can return an older cache entry. It must not
                # replace the newest primary identity for this SIM/RAT.
                continue
            if last and 0 < stamp-last[1] <= 15000 and key != last[0]:
                changes.setdefault(scope, []).append(stamp)
            previous[scope] = (key, stamp)
    findings = []
    for key, samples in groups.items():
        sub, radio, identity, *_ = json.loads(key)
        label = f'{sub} {radio} cell {identity[2]}'
        power = 'rsrp' if radio == 'LTE' else 'ss_rsrp'
        # Split around missing values or sampling gaps; do not interpolate evidence.
        for metric, threshold in ((power, -110),):
            segments, segment = [], []
            for stamp, signals in samples:
                value = signals.get(metric, {}).get('value')
                if value is None or (segment and stamp-segment[-1][0] > 15000):
                    segments.append(segment); segment = []
                if value is not None: segment.append((stamp, value))
            segments.append(segment)
            for segment in segments:
                if len(segment) < 5 or segment[-1][0]-segment[0][0] < 10000: continue
                weak = sum(v <= threshold for _, v in segment)
                if weak / len(segment) >= .8:
                    findings.append(finding('CELL-SUSTAINED', label + ': repeated weak coverage',
                        f'{weak}/{len(segment)} fresh {metric.upper()} samples at or below {threshold} dBm over {(segment[-1][0]-segment[0][0])/1000:g} seconds.',
                        'Weak signal persisted across observed samples; this does not establish continuous coverage or a service outage.',
                        'Repeat at a second position with the same cell and phone orientation; compare signal and phone-bound service tests.',
                        cell=key, metric=metric, sample_count=len(segment), weak_samples=weak,
                        start_ms=segment[0][0], end_ms=segment[-1][0]))
                    break
        for metric, drop in ((('rsrq' if radio == 'LTE' else 'ss_rsrq'), 6),
                             (('rssnr' if radio == 'LTE' else 'ss_sinr'), 8)):
            for before, middle, after in zip(samples, samples[1:], samples[2:]):
                values = [s[1].get(metric, {}).get('value') for s in (before, middle, after)]
                if any(v is None for v in values) or after[0]-before[0] > 15000: continue
                if min(values[0], values[2])-values[1] >= drop:
                    findings.append(finding('CELL-DIP', label + ': recovered radio-quality drop',
                        f'{metric.upper()} changed {values[0]:g} to {values[1]:g} to {values[2]:g} dB across three fresh samples.',
                        'Quality dropped and recovered at the sampled instants. Load, radio conditions and movement remain possible explanations.',
                        'Repeat while stationary and compare against a phone-bound loss/latency test; do not correlate unrelated desktop traffic.',
                        cell=key, metric=metric, values=values, sample_times_ms=[before[0], middle[0], after[0]]))
                    break
    for (sub, radio), stamps in changes.items():
        count = max((sum(0 <= t-start <= 60000 for t in stamps) for start in stamps), default=0)
        if count >= 3:
            findings.append(finding('CELL-CHANGES', f'{sub} {radio}: repeated primary-cell changes',
                f'{count} observed primary-cell identity changes within a 60-second window.',
                'Changing registered identities is not proof of handover failure; normal mobility and network selection can cause changes.',
                'Repeat stationary, keeping the same SIM, and compare phone-bound service symptoms before diagnosing instability.',
                subscription=sub, radio=radio, changes=count, change_times_ms=stamps))
    return dict(version=VERSION, qualified_samples=qualified, excluded_samples=excluded, omitted_samples=omitted,
        findings=findings[:64], omitted_findings=max(0, len(findings)-64),
        limitation='Only independent registered LTE/NR samples with known age <=10 seconds and exposed cell identity qualify. Gaps are not filled; unknown, old and repeated samples are excluded.')


def spectrum_patterns(sweeps, low, high):
    result = dict(version=VERSION, findings=[], sweep_count=len(sweeps), limitation=
        'Reconstructed sweep order, not elapsed time or transmitter duty cycle. Relative uncalibrated power cannot identify interference or a carrier.')
    if len(sweeps) < 5:
        result['reason'] = 'At least five matching complete sweeps are required.'; return result
    maps = [{(a, b): v for a, b, v in sweep} for sweep in sweeps]
    keys = sorted(maps[0])
    if not keys or any(m.keys() != maps[0].keys() for m in maps):
        result['reason'] = 'Frequency coverage differs between sweeps.'; return result
    end = low
    for a, b in keys:
        if a > end + 1e-8 or b <= a or a < end - 1e-8:
            result['reason'] = 'Missing or overlapping frequency bins.'; return result
        end = b
    if abs(end-high) > 1e-8 or any(not math.isfinite(v) for m in maps for v in m.values()):
        result['reason'] = 'Incomplete or nonfinite frequency coverage.'; return result
    floors = [statistics.median(sorted(m.values())[:max(1, len(keys)//5)]) for m in maps]
    persistent, bursts = [], []
    for key in keys:
        active = sum(m[key] > floor+10 for m, floor in zip(maps, floors))
        if active/len(maps) >= .8: persistent.append((key, active))
        elif 0 < active/len(maps) <= .2: bursts.append((key, active))
    for code, title, bins, fraction in [('SDR-PERSISTENT', 'Persistent sampled spectrum activity', persistent, 'at least 80%'),
                              ('SDR-BURST', 'Brief sampled spectrum activity', bursts, 'at most 20%')]:
        if bins:
            result['findings'].append(finding(code, title,
                f'{len(bins)} frequency bins exceeded each sweep\'s estimated floor by 10 dB in {fraction} of {len(maps)} reconstructed sweeps.',
                'This describes observed frequency-bin activity, not a detected transmitter or harmful interference.',
                'Inspect the waterfall at these frequencies; repeat with identical receiver settings and correlate with affected-service measurements.',
                bin_count=len(bins), sweep_count=len(maps), bins=[dict(min_mhz=k[0], max_mhz=k[1], active_sweeps=n) for k,n in bins[:20]], bins_listed=min(20,len(bins))))
    delta = statistics.median(floors[-3:])-statistics.median(floors[:3])
    broad = sum(statistics.median([m[k] for m in maps[-3:]])-statistics.median([m[k] for m in maps[:3]]) >= 8 for k in keys)/len(keys)
    if len(maps) >= 6 and delta >= 8 and broad >= .8:
        result['findings'].append(finding('SDR-FLOOR', 'Broad received-power rise within capture',
            f'Estimated floor rose {delta:+.1f} dB; {broad*100:.0f}% of bins rose at least 8 dB (first three versus last three sweeps).',
            'Broad received energy increased. Antenna movement, receiver changes and the RF environment are alternative causes; this is not confirmed interference.',
            'Repeat with fixed antenna position and unchanged gain; compare a matched baseline and service symptoms.',
            floor_delta_db=delta, raised_bin_fraction=broad, sweep_count=len(maps)))
    result['reason'] = 'Assessed matching complete reconstructed sweeps.'
    return result


def patterns_html(result):
    esc = lambda value: escape(str(value))
    parts = ['<h3>Capture diagnostics</h3>']
    if 'qualified_samples' in result:
        parts.append(f"<p>{result['qualified_samples']} qualified samples; {result['excluded_samples']} excluded samples.</p>")
        if result.get('omitted_samples') or result.get('omitted_findings'):
            parts.append(f"<p>Analysis limits: {result.get('omitted_samples', 0)} samples and {result.get('omitted_findings', 0)} findings omitted (128 cells / 64 findings maximum).</p>")
    if not result['findings']:
        parts.append('<p>' + esc(result.get('reason', 'No qualifying temporal pattern detected. This does not establish service health.')) + '</p>')
    for item in result['findings']:
        parts.append('<h4>' + esc(item['title']) + '</h4><p>' + esc(item['observation']) + '</p><p>' + esc(item['interpretation']) + '</p><p><b>Next field test:</b> ' + esc(item['next_test']) + '</p>')
        if item['evidence'].get('bins'):
            parts.append('<table><tr><th>Frequency interval (MHz)</th><th>Active / sampled sweeps</th></tr>')
            for bin in item['evidence']['bins']:
                parts.append(f"<tr><td>{bin['min_mhz']:g} to {bin['max_mhz']:g}</td><td>{bin['active_sweeps']} / {item['evidence']['sweep_count']}</td></tr>")
            parts.append('</table><p>First ' + str(item['evidence']['bins_listed']) + ' matching bins shown; adjacent bins may represent one signal.</p>')
    parts.append('<p>' + esc(result['limitation']) + '</p>')
    return ''.join(parts)


def apply_patterns(report, result, source):
    """Add source-labelled observations without mixing receiver health scores."""
    from . import core
    report.normalized_metrics.setdefault('capture_diagnostics', {})[source] = result
    for index, item in enumerate(result['findings']):
        core.VeilbreakerLogicEngine._finding(report.findings,
            source + '-' + item['id'] + '-' + str(index), core.Severity.NOTICE,
            core.Domain.SDR if item['id'].startswith('SDR') else core.Domain.CELLULAR_RF,
            source + ': ' + item['title'], item['observation'], item['interpretation'],
            item['next_test'], .7, ['capture_diagnostics'])
    if result['findings']:
        report.summary.append(source + ': ' + str(len(result['findings'])) +
            ' capture-local patterns found. These observations do not establish a service failure; see Findings and the receiver report for supporting samples and next tests.')
