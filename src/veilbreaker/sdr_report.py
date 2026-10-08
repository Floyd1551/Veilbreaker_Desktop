"""Standalone, conservative SDR diagnostics from saved receive-only evidence."""
import hashlib
import csv
from html import escape
import json
import math
from pathlib import Path
import statistics
from .bandplan import default_plan, bands_at, NOTICE, band_description
from .rf_workflow import read_trace
from .band_summary import summarize_bands


def observed_intervals(path, low, high):
    """Actual CSV bin widths, independent of gaps in summary-derived spacing."""
    intervals = set()
    widths = set()
    with path.open(encoding='utf-8', errors='replace', newline='') as stream:
        for row in csv.reader(stream):
            if len(row) < 7:
                continue
            try:
                start, width = float(row[2])/1e6, float(row[4])/1e6
                powers = [float(value) for value in row[6:] if value.strip()]
            except ValueError:
                continue
            if not math.isfinite(start) or not math.isfinite(width) or width <= 0:
                continue
            for index, power in enumerate(powers):
                center = start + (index+0.5)*width
                if math.isfinite(power) and low <= center < high:
                    intervals.add((max(low, start+index*width), min(high, start+(index+1)*width)))
                    widths.add(width*1e6)
    return sorted(intervals), sorted(widths)


def build_sdr_report(summaries, metadata, plan=None):
    plan = default_plan() if plan is None else plan
    result = {'schema_version': 1, 'metadata': dict(metadata), 'band_plan': plan, 'ranges': [],
              'limitations': 'Relative, uncalibrated dB; not dBm or a compliance measurement. A sweep cannot identify a protocol, transmitter, or cause of interference. Frequency-bin activity is not time occupancy. ' + NOTICE}
    for summary in summaries:
        row = {'label': summary.get('label', 'Unnamed'), 'requested_min_mhz': summary.get('min_mhz'),
               'requested_max_mhz': summary.get('max_mhz'), 'bin_width_hz': summary.get('bin_width_hz'),
               'status': 'unavailable', 'bin_count': 0, 'coverage_pct': None, 'peak': None, 'capture': None,
               'notes': [], 'csv_path': summary.get('csv_path'), 'sha256': None}
        result['ranges'].append(row)
        try:
            path = Path(summary['csv_path'])
            with path.open('rb') as stream:
                row['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            points = read_trace(summary)
            if not points or any(not all(math.isfinite(v) for v in p) for p in points):
                raise ValueError('No usable finite spectrum samples.')
            low, high = float(summary['min_mhz']), float(summary['max_mhz'])
            if not math.isfinite(high-low) or high <= low:
                raise ValueError('Invalid recorded range.')
            # Union of bin intervals: overlaps must not inflate frequency coverage.
            intervals, widths = observed_intervals(path, low, high)
            row['observed_bin_widths_hz'] = widths
            row['band_summaries'] = summarize_bands(points, intervals, plan, low, high)
            covered, end = 0.0, low
            for start, stop in intervals:
                covered += max(0, stop-max(start, end))
                end = max(end, stop)
            row['coverage_pct'] = round(min(100, covered / (high-low) * 100), 2)
            row['bin_count'] = len(points)
            row['observed_min_mhz'], row['observed_max_mhz'] = points[0][0], points[-1][0]
            row['status'] = 'partial' if row['coverage_pct'] < 99.99 else 'metadata unknown'
            try:
                capture = json.loads(path.with_suffix('.capture.json').read_text(encoding='utf-8'))
                if not isinstance(capture, dict):
                    raise ValueError('Capture metadata is not an object.')
                row['capture'] = capture
                if capture.get('returncode') != 0:
                    row['status'] = 'partial'
                    row['notes'].append('Acquisition did not record a successful exit; results may be incomplete.')
                elif row['status'] != 'partial':
                    row['status'] = 'recorded success'
            except (OSError, ValueError):
                row['notes'].append('Acquisition settings/status unavailable; completion cannot be verified.')
            peak = max(points, key=lambda p: p[2])
            row['peak'] = {'frequency_mhz': peak[0], 'median_db': peak[1], 'maximum_db': peak[2],
                           'expected_uses': [band_description(b) for b in bands_at(plan, peak[0])]}
            medians = sorted(p[1] for p in points)
            floor = statistics.median(medians[:max(1, len(medians)//5)])
            row['estimated_floor_db'] = floor
            row['strongest_bins'] = [
                {'frequency_mhz': p[0], 'median_db': p[1], 'maximum_db': p[2],
                 'median_above_floor_db': round(p[1]-floor, 3),
                 'expected_uses': [band_description(b) for b in bands_at(plan, p[0])]}
                for p in sorted(points, key=lambda p: (-p[2], p[0]))[:10]]
            row['bins_above_floor_plus_10db_pct'] = round(100 * sum(p[1] > floor+10 for p in points)/len(points), 2)
            row['notes'].append('Floor estimate: median of lowest 20% of bin medians (at least one). Activity: fraction of observed bin medians > floor + 10 dB; not time occupancy. Strong wideband signals can bias this estimate.')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            row['notes'].append(f'Saved spectrum unavailable: {exc}')
    return result


def report_html(report, interactive=False, technical=True):
    esc = lambda value: escape(str(value))
    foreground = '#dee7f2' if interactive else '#172131'
    muted = '#a7b8cb' if interactive else '#536579'
    accent = '#75e1ce' if interactive else '#146754'
    border = '#354960' if interactive else '#d5dee8'
    parts = ['<!doctype html><html><head><meta charset="utf-8"><title>SDR survey report</title>',
             f'<style>body, p, td, th {{font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; color: {foreground};}} '
             f'body {{max-width:1050px; margin:16px auto; padding:12px;}} h1 {{font-size:24px; font-weight:600;}} '
             f'h2 {{font-size:19px; margin-top:24px;}} h3 {{font-size:15px; margin-top:20px;}} '
             f'a {{color:{accent};}} .muted {{color:{muted};}} table {{border-collapse:collapse; width:100%;}} '
             f'td, th {{border:1px solid {border}; padding:8px; text-align:left;}} '
             'pre {font-family: Consolas, monospace; font-size:11px; white-space:pre-wrap;}</style></head><body>',
             '<h1>SDR survey report</h1>',
             '<p class="muted">' + esc(report['metadata'].get('site_id', 'Site not recorded')) + ' &nbsp; / &nbsp; ' + esc(report['metadata'].get('run_id', 'Run not recorded')) + '</p>',
             '<p class="muted">Relative power, uncalibrated. Band and carrier labels are reference context, not detected identities.</p>']
    if not report['ranges']:
        parts.append('<p>No SDR capture evidence in this run.</p>')
    for range_index, row in enumerate(report['ranges']):
        status = {'metadata unknown': 'Capture settings unavailable', 'recorded success': 'Capture completed',
                  'partial': 'Partial capture', 'unavailable': 'Evidence unavailable'}.get(row['status'], row['status'])
        parts.extend(['<section><h2>' + esc(row['label']) + '</h2>',
                      '<p class="muted">' + esc(status) + ' &nbsp; · &nbsp; ' + str(row['bin_count']) + ' observed bins &nbsp; · &nbsp; ' + esc(row['requested_min_mhz']) + '–' + esc(row['requested_max_mhz']) + ' MHz</p>'])
        if row['peak']:
            p = row['peak']
            parts.append(f"<table cellpadding=\"10\"><tr><td>Strongest bin<br><b>{p['frequency_mhz']:.3f} MHz</b></td><td>Maximum relative power<br><b>{p['maximum_db']:.1f} dB</b></td><td>Frequency coverage<br><b>{row['coverage_pct']:g}%</b></td></tr></table>")
            context = ', '.join(p['expected_uses']) or 'No reference entry'
            if interactive and not technical:
                context = '; '.join(item.split(' | ')[0] for item in p['expected_uses'][:2]) or 'No reference entry'
                if len(p['expected_uses']) > 2:
                    context += f"; {len(p['expected_uses'])-2} more overlapping references in the band table"
            parts.append('<p class="muted">Expected uses: ' + esc(context) + '.</p>')
            if technical:
                parts.append('<p>Observed bin widths: ' + esc(', '.join(f'{w/1000:g} kHz' for w in row['observed_bin_widths_hz'])) + '</p>')
            parts.append(f"<p>Estimated floor: {row['estimated_floor_db']:.1f} relative dB. Observed bins above floor + 10 dB: {row['bins_above_floor_plus_10db_pct']:g}%.</p>")
            parts.append('<h3>Band survey summary</h3><p class="muted">' + ('Select a band to inspect it. ' if interactive else '') + 'Coverage is measured against the full reference band. Overlapping bands share measurements; unavailable means unresolved, not quiet.</p>')
            if not row.get('band_summaries'):
                parts.append('<p>No reference bands overlap this capture.</p>')
            else:
                parts.append('<table border="1" cellspacing="0" cellpadding="6"><tr><th>Band / carrier / direction</th><th>Full-band coverage</th><th>Bins</th><th>Median relative dB</th><th>Maximum relative dB</th></tr>')
                for band_index, band in enumerate(row['band_summaries']):
                    title = esc(band['label'])
                    if interactive:
                        title = f'<a href="sdr-band:{range_index}:{band_index}">{title}</a>'
                    median = 'Unavailable' if band['median_bin_power_db'] is None else f"{band['median_bin_power_db']:.1f}"
                    maximum = 'Unavailable' if band['maximum_db'] is None else f"{band['maximum_db']:.1f}"
                    parts.append(f"<tr><td>{title}<br>{esc(band['carrier'])}<br>{esc(band['direction'])}</td><td>{band['full_band_coverage_pct']:g}%<br>{esc(band['coverage_status'])}</td><td>{band['bin_count']}</td><td>{median}</td><td>{maximum}</td></tr>")
                parts.append('</table>')
            parts.append('<h3>Strongest observed bins</h3><p>Ranked by maximum relative power. Adjacent bins may belong to the same signal; these are not separate transmitter detections.</p>')
            parts.append('<table border="1" cellspacing="0" cellpadding="6"><tr><th>MHz</th><th>Maximum dB</th><th>Median dB</th><th>Median above estimated floor (dB)</th><th>Reference context</th></tr>')
            for rank, point in enumerate(row.get('strongest_bins', [])):
                frequency = f"{point['frequency_mhz']:.3f}"
                if interactive:
                    frequency = f'<a href="sdr-bin:{range_index}:{rank}">{frequency}</a>'
                parts.append(f"<tr><td>{frequency}</td><td>{point['maximum_db']:.1f}</td><td>{point['median_db']:.1f}</td><td>{point['median_above_floor_db']:+.1f}</td><td>{esc('; '.join(point['expected_uses']) or 'No reference entry')}</td></tr>")
            parts.append('</table>')
        parts.append('<p class="muted">' + '<br>'.join(esc(n) for n in row['notes']) + '</p>')
        if technical:
            parts.extend([
                      '<h3>Acquisition metadata</h3><pre>' + (esc(json.dumps(row['capture'], indent=2, ensure_ascii=False)) if row['capture'] is not None else 'Unavailable') + '</pre>',
                      '<p>Source: ' + esc(row['csv_path']) + '<br>SHA-256: ' + esc(row['sha256']) + '</p>'])
        parts.append('</section>')
    parts.append('<h2>How to interpret this report</h2><p class="muted">' + esc(report['limitations']) + ' Band medians summarize bin medians, not integrated band power. Center-frequency markers are excluded from band summaries.</p>')
    parts.append('<p class="muted">Reference: ' + esc(report['band_plan']['name']) + ' / ' + esc(report['band_plan']['version']) + '</p>')
    if technical:
        parts.append('<h2>Run metadata</h2><pre>' + esc(json.dumps(report['metadata'], indent=2, ensure_ascii=False)) + '</pre>')
        parts.append('<h2>Reference sources</h2>' + ''.join('<p class="muted">' + esc(source) + '</p>' for source in sorted({b['source'] for b in report['band_plan']['bands']})))
    parts.append('</body></html>')
    return ''.join(parts)
